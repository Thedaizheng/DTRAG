import os
import pymysql
from rag.kdb.db.doc_tree import DocTree, DocTreeNode
from dotenv import load_dotenv

class DBMySQL:
    def __init__(self):
        load_dotenv()
        self.conn = pymysql.connect(
            host=os.getenv("mysql_host"),
            user=os.getenv("mysql_user"),
            password=os.getenv("mysql_password"),
            database=os.getenv("mysql_database"),
            cursorclass=pymysql.cursors.DictCursor  # 设置游标类型为字典游标，返回字典类型的结果
        )

    def create_doc(self, doc_group, doc_name, doc_formatted):
        with self.conn.cursor() as cursor:
            doc_id = -1
            cursor.execute("select * from doc where name=%s", (doc_name))
            rs = cursor.fetchone()
            if rs is None:
                cursor.execute(
                    "INSERT INTO doc (`doc_group`, `name`) VALUES (%s, %s) ",
                    (doc_group, doc_name),
                )
                self.conn.commit()
                doc_id = cursor.lastrowid

            else:
                doc_id = rs["id"]

            cursor.execute(
                "INSERT INTO doc_ver (`doc_id`, `status`) VALUES(%s, %s)",
                (doc_id, 0)
            )
            self.conn.commit()
            doc_ver_id = cursor.lastrowid

            doc_node_ids = []
            doc_ver_ids = []
            for one in doc_formatted:
                doc_node_id = self.get_node_id(doc_id, doc_ver_id, one["id"])
                cursor.execute(
                    "INSERT INTO doc_nodes(`id`, `doc_id`, `doc_ver_id`,  `parent_id`, `level`, `seq`, `content`) VALUES(%s, %s, %s, %s, %s, %s, %s)",
                    (
                        doc_node_id,
                        doc_id,
                        doc_ver_id,
                        self.get_node_id(doc_id, doc_ver_id, one["parent_id"]),
                        one["level"],
                        one["seq_index"],
                        one["content"]
                    )
                )
                self.conn.commit()

                doc_node_ids.append(doc_node_id)
                doc_ver_ids.append(doc_ver_id)

        return doc_node_ids, doc_ver_ids

    def get_node_id(self, doc_id, doc_ver_id, id):
        if id == -1 or id == "-1":
            return -1

        return doc_id*1000000 + doc_ver_id * 10000 + int(id)

    def add_node_na(self, doc_nodes_id, content):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO doc_nodes_da (`doc_nodes_id`, `content`) VALUES (%s, %s) ",
                (doc_nodes_id, content),
            )
            self.conn.commit()

            cursor.execute(
                "select * from doc_nodes where id=%s", (doc_nodes_id))
            doc_node = cursor.fetchone()
            if doc_node is None:
                return "", ""

            cursor.execute("select * from doc where id=%s",
                           (doc_node["doc_id"]))
            doc = cursor.fetchone()
            if doc is None:
                return "", ""

            return doc["doc_group"], doc_node["doc_ver_id"]

    def search(self, doc_nodes_id, configs):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "select * from doc_nodes where id=%s", (doc_nodes_id))
            doc_node = cursor.fetchone()
            if doc_node is None:
                return None

            docTree = DocTree()
            docTree.addNode(
                DocTreeNode(
                    doc_node['id'], doc_node['parent_id'],
                    doc_node['seq'], doc_node['content']
                ),
                True
            )

            # 获取同层节点
            self.get_same_layer_doc_nodes(doc_node, docTree)
            # 获取父节点
            self.get_parent_layer_doc_nodes(
                doc_node, docTree, configs["ParentLayerDeep"])
            # 获取子节点
            self.get_child_layer_doc_nodes(
                doc_node, docTree, configs["ParentLayerSize"])

            docTree.buildTree()

            # 裁剪Tree，同级节点保留300，父级保留500，下级保留200
            docTree.cropTree(configs["SameLayerSize"],
                             configs["ParentLayerSize"],
                             configs["ChildLayerSize"])

            return docTree.toStr()

    def get_same_layer_doc_nodes(self, doc_node, docTree):
        with self.conn.cursor() as cursor:
            cursor.execute("select * from doc_nodes where parent_id=%s order by seq asc",
                           (doc_node['parent_id']))
            for one in cursor.fetchall():
                docTree.addNode(DocTreeNode(
                    one['id'], one['parent_id'], one['seq'], one['content']))

    def get_child_layer_doc_nodes(self, doc_node, docTree, deep=0):
        with self.conn.cursor() as cursor:
            cursor.execute("select * from doc_nodes where parent_id=%s",
                           (doc_node['id']))
            for one in cursor.fetchall():
                docTree.addNode(DocTreeNode(
                    one['id'], one['parent_id'], one['seq'], one['content']))
                if deep > 0:
                    self.get_child_layer_doc_nodes(one, docTree, deep-1)

    def get_parent_layer_doc_nodes(self, doc_node, docTree, deep=0):
        with self.conn.cursor() as cursor:
            cursor.execute("select * from doc_nodes where id=%s",
                           (doc_node['parent_id']))
            for one in cursor.fetchall():
                docTree.addNode(DocTreeNode(
                    one['id'], one['parent_id'], one['seq'], one['content']))
                # 额外检索父节点的同级节点
                self.get_same_layer_doc_nodes(one, docTree)
                if deep > 0:
                    self.get_parent_layer_doc_nodes(one, docTree, deep-1)

    def get_doc_group_permission(self, doc_group=""):
        with self.conn.cursor() as cursor:
            if doc_group == "":
                cursor.execute("select * from doc_group_permission")
            else:
                cursor.execute(
                    "select * from doc_group_permission where doc_group=%s", (doc_group))

            return cursor.fetchall()

    def add_doc_group_permission(self, doc_group, allowed_users):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO doc_group_permission (`doc_group`, `allowed_users`)" +
                " VALUES (%s, %s) ON DUPLICATE KEY UPDATE allowed_users = %s",
                (doc_group, allowed_users, allowed_users)
            )
            self.conn.commit()

    def publish_doc_ver(self, doc_ver_id):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "select * from doc_ver where id=%s",
                (doc_ver_id)
            )
            rs = cursor.fetchone()
            if rs is None:
                return

            cursor.execute(
                "update doc_ver set status=0 where doc_id=%s", (rs["doc_id"]))
            cursor.execute(
                "update doc_ver set status=1 where id=%s", (doc_ver_id)
            )

            self.conn.commit()

    def publish_lastest_doc_ver(self, doc_name):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "select * from doc where name=%s",
                (doc_name)
            )
            rs = cursor.fetchone()
            if rs is None:
                return
            doc_id = rs["id"]

            # 查找doc_id的最大版本号
            cursor.execute(
                "select max(id) as id from doc_ver where doc_id=%s", (doc_id))
            rs = cursor.fetchone()
            if rs is None:
                return

            cursor.execute(
                "update doc_ver set status=0 where doc_id=%s", (doc_id))
            cursor.execute(
                "update doc_ver set status=1 where id=%s", (rs["id"]))

            self.conn.commit()

    def get_lastest_doc_ver_ids(self, doc_group):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "select * from doc where doc_group=%s",
                (doc_group)
            )

            lastest_doc_ver_ids = []
            for one in cursor.fetchall():
                cursor.execute(
                    "select * from doc_ver where doc_id=%s and status=1",
                    (one["id"])
                )
                rs = cursor.fetchone()
                if rs is not None:
                    lastest_doc_ver_ids.append(rs["id"])

            return lastest_doc_ver_ids


def init_db():
    """
    需要谨慎调用，会清空数据库
    """
    conn = pymysql.connect(
        host=os.getenv("mysql_host"),
        user=os.getenv("mysql_user"),
        password=os.getenv("mysql_password"),
        cursorclass=pymysql.cursors.DictCursor
    )

    with conn.cursor() as cursor:
        cursor.execute("DROP DATABASE IF EXISTS " +
                       os.getenv("mysql_database"))
        conn.commit()
        cursor.execute("CREATE DATABASE " + os.getenv("mysql_database"))
        conn.commit()

        cursor.execute("USE " + os.getenv("mysql_database"))

        with open("./rag/kdb/db/sql.sql", 'r', encoding='utf-8') as sql_file:
            sql_queries = sql_file.read().split(';')
            for sql_query in sql_queries:
                if sql_query.strip():
                    cursor.execute(sql_query)
            conn.commit()

    conn.close()
