class Session:
    def __init__(self) -> None:
        # 要读取的文件路径
        self.file_path = ""
        # 读取后的文件内容
        self.text = ""
        # 结构化之后的文件内容
        self.text_formatted = []
        # doc group
        self.doc_group = "default"
        # doc 名称
        self.doc_name = ""
        # 添加文档后，是否直接发布
        self.need_publish = False


class BaseDocHandler:
    def __init__(self):
        pass

    def __or__(self, other):
        if not hasattr(self, "actions"):
            self.actions = [self]

        if isinstance(other, BaseDocHandler):
            self.actions.append(other)
        elif isinstance(other, str):
            self.sess = Session()
            self.sess.filePath = other

        return self

    def exec(self, sess=None):
        self.sess = sess
        for one in self.actions:
            one.run(self.sess)

    def run(self, sess: Session):
        pass
