from rag.kdb.doc_handler import base
from rag.kdb.db import db
from rag.kdb.manager import manager


class Saver(base.BaseDocHandler):
    def run(self, sess: base.Session):
        if sess.text_formatted is None:
            return

        db.instance.add_doc(sess.doc_group, sess.doc_name, sess.text_formatted)

        if sess.need_publish:
            manager.instance.publish_lastest_doc_ver(sess.doc_name)
