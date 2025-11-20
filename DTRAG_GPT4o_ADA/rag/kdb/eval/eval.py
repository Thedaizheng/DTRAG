from rag.kdb.eval import tru_tester
from trulens_eval import Tru
import time


class Eval:
    def eval(self, doc_group, test_dataset=[]):
        eval_ver = doc_group + str(round(time.time()))
        tru_app, tester = tru_tester.build_tru_app(eval_ver, doc_group)

        if len(test_dataset) > 0:
            with tru_app:
                for one in test_dataset:
                    tester.query(one)

        self.show(eval_ver)

    def show(self, eval_ver):
        tru = Tru()
        tru.get_leaderboard(app_ids=[eval_ver])
        tru.run_dashboard()


intance = Eval()
