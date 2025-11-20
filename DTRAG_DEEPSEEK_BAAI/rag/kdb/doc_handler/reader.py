from rag.kdb.doc_handler import base
from docx import Document


class Reader(base.BaseDocHandler):
    def __init__(self):
        super().__init__()
        self.readers = {
            "default": self.normal,
            "docx": self.word
        }

    def run(self, sess: base.Session):
        file_suffix = sess.file_path.split(".")[-1]
        reader_func = self.readers.get(file_suffix)
        if reader_func is None:
            sess.text = self.normal(sess.file_path)
        else:
            sess.text = reader_func(sess.file_path)

    # 普通文件
    def normal(self, file_path):
        with open(file_path, 'r',encoding='utf-8') as file:
            content = file.read()

        return content

    # word文件
    def word(self, file_path):
        doc = Document(file_path)
        full_text = []
        # 遍历文档中的每一个段落，并将其文本添加到列表中
        for para in doc.paragraphs:
            full_text.append(para.text)
        # 将列表中的所有文本连接成一个字符串，并返回
        return '\n'.join(full_text)
