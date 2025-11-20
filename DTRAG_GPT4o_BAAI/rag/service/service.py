# import os
# import openai
# from rag.kdb.query import query
# import copy
# import json
# from rag.tools.tools import Tools
# from dotenv import load_dotenv
# load_dotenv()
#
# class Service:
#     def __init__(self):
#         self.client = openai.OpenAI(base_url = "http://chatapi.littlewheat.com/v1",api_key=os.getenv("api_key"))
#         self.tools = Tools()
#
#     def handle_user_chat(self, prompt, messages, user, doc_group, need_semantic_analysis=False):
#         search_text = prompt
#         if need_semantic_analysis:
#             search_text = self.semantic_analysis_user_prompt(prompt, messages)
#
#         print("user:", user)
#         print("doc_group:", doc_group)
#         print("search_text:", search_text)
#         rs = query.instance.query(user, doc_group, search_text, False)
#         print("向量数据库查询结果：", rs)
#         if rs == "":
#             messages.append({
#                 "role": "user",
#                 "content": prompt
#             })
#         else:
#             messages.append(
#                 {
#                     "role": "user",
#                     "content": f"请参考知识库：'''{rs}'''，回答用户的问题'''{prompt}'''，不要告知用户你参考了知识库进行回答"
#                 }
#             )
#
#         response = self.client.chat.completions.create(
#             messages=messages,
#             model=os.getenv("gpt_model"),
#             top_p=0.2,
#             stream=True,
#             tool_choice="auto",
#             tools=self.tools.tools_define()
#         )
#
#         # 命中了插件
#         for bingoTool, content in self.tools.tool_call_stream(response, messages):
#             if bingoTool:
#                 yield content
#
#         # 正常消息
#         if not bingoTool:
#             msg = ""
#             for one in response:
#                 chunk = one.choices[0].delta
#                 if chunk.content is not None:
#                     msg += chunk.content
#                     yield msg
#
#     def semantic_analysis_user_prompt(self, prompt, messages):
#         if len(messages) < 2:
#             return prompt
#
#         msgs = copy.deepcopy(messages)
#         msgs.append({
#             "role": "user",
#             "content": f'''请你基于上下文理解一下用户输入的问题''{prompt}''，然后输出用户真正想问的问题，并以json的格式返回，json格式：{{"purpose":""}}'''
#         })
#
#         chat_completion = self.client.chat.completions.create(
#             messages=msgs,
#             model=os.getenv("gpt_model"),
#             top_p=0.2,
#             response_format={"type": "json_object"},
#             stream=False
#         )
#
#         return json.loads(chat_completion.choices[0].message.content)["purpose"]
#
#     def system_role(self):
#         return "Dzzzz的智能客服助手"
#
#
# instance = Service()
import os
import openai
from rag.kdb.query import query
import copy
import json
from rag.tools.tools import Tools
from dotenv import load_dotenv
load_dotenv()

class Service:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url="http://chatapi.littlewheat.com/v1",
            api_key=os.getenv("api_key")
        )
        self.tools = Tools()

    def handle_user_chat(self, prompt, messages, user, doc_group, need_semantic_analysis=False):
        search_text = prompt
        if need_semantic_analysis:
            search_text = self.semantic_analysis_user_prompt(prompt, messages)

        print("user:", user)
        print("doc_group:", doc_group)
        print("search_text:", search_text)

        rs = query.instance.query(user, doc_group, search_text, False)
        print("向量数据库查询结果：", rs)

        # 去重 & 过滤空条目
        if isinstance(rs, list):
            rs = list(set([d.strip() for d in rs if d.strip()]))
        else:
            rs = [rs] if rs.strip() else []

        # 拼接参考知识
        if rs:
            messages.append({
                "role": "user",
                "content": f"请参考知识库：'''{rs}'''，回答用户的问题'''{prompt}'''，不要告知用户你参考了知识库进行回答"
            })
        else:
            messages.append({
                "role": "user",
                "content": prompt
            })

        response = self.client.chat.completions.create(
            messages=messages,
            model=os.getenv("gpt_model"),
            top_p=0.2,
            stream=True,
            tool_choice="auto",
            tools=self.tools.tools_define()
        )

        msg = ""
        # 命中了插件
        for bingoTool, content in self.tools.tool_call_stream(response, messages):
            if bingoTool:
                yield content

        # 正常消息
        try:
            for one in response:
                # 安全检查
                if not hasattr(one, "choices") or not one.choices:
                    continue
                delta = one.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    msg += delta.content
                    yield msg
        except Exception as e:
            print("流式返回处理异常:", e)

    def semantic_analysis_user_prompt(self, prompt, messages):
        if len(messages) < 2:
            return prompt

        msgs = copy.deepcopy(messages)
        msgs.append({
            "role": "user",
            "content": f'''请你基于上下文理解一下用户输入的问题''{prompt}''，然后输出用户真正想问的问题，并以json的格式返回，json格式：{{"purpose":""}}'''
        })

        chat_completion = self.client.chat.completions.create(
            messages=msgs,
            model=os.getenv("gpt_model"),
            top_p=0.2,
            response_format={"type": "json_object"},
            stream=False
        )

        return json.loads(chat_completion.choices[0].message.content)["purpose"]

    def system_role(self):
        return "Dzzzz的智能客服助手"

instance = Service()
