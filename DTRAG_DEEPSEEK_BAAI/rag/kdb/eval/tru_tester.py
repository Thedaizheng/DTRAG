from trulens_eval import Tru
from trulens_eval.tru_custom_app import instrument
from trulens_eval import Feedback, Select
from trulens_eval.feedback import Groundedness
from trulens_eval.feedback.provider.openai import OpenAI as fOpenAI
from trulens_eval import TruCustomApp
import numpy as np
import openai
import os
from rag.kdb.query import query


class TruTester:
    def __init__(self, doc_group):
        self.doc_group = doc_group

    @instrument
    def retrieve(self, text: str) -> list:
        return query.instance.query("", self.doc_group, text)

    @instrument
    def generate_completion(self, text: str, context_str: list) -> str:
        client = openai.OpenAI(api_key=os.getenv("api_key"))
        completion = client.chat.completions.create(
            model=os.getenv("gpt_model"),
            temperature=0,
            messages=[{
                "role": "user",
                "content": f'''
                背景信息："""{context_str}"""
                请参考<背景信息>回答问题"""{text}"""
                '''
            }]
        ).choices[0].message.content

        return completion

    @instrument
    def query(self, text: str) -> str:
        context_str = self.retrieve(text)
        completion = self.generate_completion(text, context_str)
        return completion


def build_tru_app(app_id, doc_group):
    fopenai = fOpenAI(api_key=os.getenv("api_key"))

    grounded = Groundedness(groundedness_provider=fopenai)

    # 扎根性
    f_groundedness = (
        Feedback(grounded.groundedness_measure_with_cot_reasons,
                 name="扎根性")
        .on(Select.RecordCalls.retrieve.rets.collect())
        .on_output()
        .aggregate(grounded.grounded_statements_aggregator)
    )

    # 答案相关性
    f_qa_relevance = (
        Feedback(fopenai.relevance_with_cot_reasons, name="答案相关性")
        .on(Select.RecordCalls.retrieve.args.query)
        .on_output()
    )

    # 上下文相关性
    f_context_relevance = (
        Feedback(fopenai.qs_relevance_with_cot_reasons,
                 name="上下文相关性")
        .on(Select.RecordCalls.retrieve.args.query)
        .on(Select.RecordCalls.retrieve.rets.collect())
        .aggregate(np.mean)
    )

    tester = TruTester(doc_group)

    return TruCustomApp(tester, app_id=app_id, feedbacks=[f_groundedness, f_qa_relevance, f_context_relevance]), tester
