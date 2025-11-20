from rag.kdb.db import db_mysql, db_chromadb


class DB:
    """
    DB 对象，不直接对外，只面向 kdb 内部使用。
    适用模块：doc_handler、manager、query。
    该类封装了对 MySQL（db_mysql） 和 ChromaDB（db_chromadb）数据库的访问。
    """

    def __init__(self):
        """初始化数据库实例，分别创建 MySQL 和 ChromaDB 数据库的连接"""
        self.mysql = db_mysql.DBMySQL()
        self.chromadb = db_chromadb.DBChroma()

    def add_doc(self, doc_group, doc_name, doc_formatted):
        """
        将文档数据存入 MySQL 和 ChromaDB。
        :param doc_group: 文档所属的分组
        :param doc_name: 文档名称
        :param doc_formatted: 结构化的文档内容
        """
        doc_node_ids, doc_ver_ids = self.mysql.create_doc(
            doc_group, doc_name, doc_formatted)
        self.chromadb.add_doc(doc_group, doc_formatted, doc_node_ids, doc_ver_ids)

    def node_da(self, doc_nodes_id, content):
        """
        数据增强（Data Augmentation）：向文档节点添加新的内容。
        :param doc_nodes_id: 需要增强的文档节点 ID
        :param content: 需要新增的文本内容
        """
        doc_group, doc_ver_id = self.mysql.add_node_na(doc_nodes_id, content)
        self.chromadb.add_doc(doc_group, [{"content": content}], [doc_nodes_id], [doc_ver_id])

    def search(self, doc_group, query, doc_ver_ids, configs={
        "ParentLayerDeep": 3,
        "ParentLayerSize": 1000,
        "ChildLayerDeep": 1,
        "ChildLayerSize": 500,
        "SameLayerSize": 2000,
    }):
        """
        在 ChromaDB 进行向量搜索，并在 MySQL 获取结构化的文档信息。
        :param doc_group: 文档组名称
        :param query: 查询文本
        :param doc_ver_ids: 需要检索的文档版本 ID 列表
        :param configs: 搜索配置，包括父/子/同层文档的搜索深度与数量
        :return: 搜索到的文档结果列表
        """
        chroma_result = self.chromadb.search(doc_group, query, doc_ver_ids)
        results = []
        hasSearch = {}

        for doc_nodes_id in chroma_result:
            if doc_nodes_id in hasSearch:
                continue
            else:
                hasSearch[doc_nodes_id] = True
            rs = self.mysql.search(doc_nodes_id, configs)
            if rs == "":
                continue
            results.append(rs)
        return results

    def get_doc_group_permission(self, doc_group=""):
        """查询指定文档组的访问权限"""
        return self.mysql.get_doc_group_permission(doc_group)

    def add_doc_group_permission(self, doc_group, allowed_users):
        """设置或更新文档组的访问权限"""
        return self.mysql.add_doc_group_permission(doc_group, allowed_users)

    def publish_doc_ver(self, doc_ver_id):
        """发布指定的文档版本"""
        self.mysql.publish_doc_ver(doc_ver_id)

    def publish_lastest_doc_ver(self, doc_name):
        """发布文档的最新版本"""
        self.mysql.publish_lastest_doc_ver(doc_name)

    def get_lastest_doc_ver_ids(self, doc_group):
        """获取文档组中最新的已发布版本 ID"""
        return self.mysql.get_lastest_doc_ver_ids(doc_group)


# 创建 DB 实例，供其他模块调用
instance = DB()