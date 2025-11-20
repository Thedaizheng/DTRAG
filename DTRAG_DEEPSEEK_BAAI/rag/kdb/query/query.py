from rag.kdb.db import db
from rag.kdb.manager import manager
from FlagEmbedding import FlagReranker


class Query:
    def __init__(self):
        self.reranker = None

    def query(self, user, doc_group, text, need_rerank=False):
        allowed_access_doc_ver_ids = manager.instance.get_allowed_access_doc_ver_ids(
            user, doc_group)
        if len(allowed_access_doc_ver_ids) == 0:
            return ""

        rs = db.instance.search(doc_group, text, allowed_access_doc_ver_ids)
        if need_rerank:
            return self.rerank(text, rs)

        return rs

    def rerank(self, text, querys):
        if self.reranker is None:
            self.reranker = FlagReranker(
                'BAAI/bge-reranker-base', use_fp16=True)

        # 计算分值
        cal_items = []
        for one in querys:
            cal_items.append([text, one])

        scores = self.reranker.compute_score(cal_items)

        # 基于计算的分值进行重排序
        need_sort_items = []
        for k, v in enumerate(querys):
            need_sort_items.append((v, scores[k]))

        sorted_items = sorted(
            need_sort_items, key=lambda x: x[1], reverse=True)
        rs = []
        for one in sorted_items:
            rs.append(one[0])

        return rs


instance = Query()
