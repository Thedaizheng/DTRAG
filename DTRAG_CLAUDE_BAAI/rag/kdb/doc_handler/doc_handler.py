from rag.kdb.doc_handler import reader, formatter, saver, base


class DocHandler:
    def __init__(self):
        self.handle_process = reader.Reader() | formatter.Formatter() | saver.Saver()

    def add_doc(self, doc_name, doc_filename, doc_group="default", need_publish=False):
        sess = base.Session()
        sess.file_path = "./rag/kdb/doc/" + doc_filename
        sess.doc_group = doc_group
        sess.doc_name = doc_name
        sess.need_publish = need_publish

        self.handle_process.exec(sess)


instance = DocHandler()
