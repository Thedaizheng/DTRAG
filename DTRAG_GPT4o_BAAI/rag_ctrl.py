import sys
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore")

load_dotenv()


def init(need_mock_data=False):
    """
    初始化kdb的数据库结构，第一次需要进行初始化
    """

    from rag.kdb.db import db_mysql
    db_mysql.init_db()
    from rag.kdb.db import db_chromadb
    db_chromadb.init_db()

    if need_mock_data:
        mock_data()


def auth(user, doc_group, allowed):
    """
    对用户进行doc_group的授权访问
    """

    from rag.kdb.manager import manager
    if allowed:
        manager.instance.auth_user(user, doc_group, allowed)


def mock_data():
    """
    mock数据，为了测试使用
    """

    from rag.kdb.db import db
    from rag.kdb.manager import manager

    db.instance.add_doc("default", "用户1", "用户01", [
        {
            "id": 1,
            "level": 1,
            "parent_id": -1,
            "seq_index": 1,
            "content": "用户01",
        },
    ])

    # 做了一个数据增强
    db.instance.node_da(1010001, "用户01")

    # 授权用户1访问default这个doc_group
    manager.instance.auth_user("用户1", "default", True)
    # 发布文档版本号为1的文档
    manager.instance.publish_doc_ver(1)


def add_doc():
    from rag.kdb.doc_handler import doc_handler
    from rag.kdb.manager import manager

    doc_handler.instance.add_doc(
        "address_book", "working_person.txt", "default", True)

    doc_handler.instance.add_doc(
        "age", "company_info.docx", "default", True)

    # 默认给用户1授权
    manager.instance.auth_user("用户1", "default", True)


def eval():
    from rag.kdb.eval import eval
    eval.intance.eval("default", ["用户1", "手机号", "年龄"])


if __name__ == "__main__":
    if len(sys.argv) == 0:
        exit()

    func = globals()[sys.argv[1]]

    args = {}
    for param in sys.argv[1:]:
        kv = param.split("=")
        if len(kv) != 2:
            continue
        args[kv[0]] = kv[1]

    func(**args)
