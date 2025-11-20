import os
from openai import OpenAI   # deepseek 的 SDK 兼容 openai 库调用
from rag.kdb.query import query
import copy
import json
from rag.tools.tools import Tools
from dotenv import load_dotenv
load_dotenv()

class Service:
    def __init__(self):
        # 使用 deepseek 的 api_key 和 base_url
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
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
        if rs == "":
            messages.append({
                "role": "user",
                "content": prompt
            })
        else:
            messages.append(
                {
                    "role": "user",
                    "content": f"请参考知识库：'''{rs}'''，回答用户的问题'''{prompt}'''，不要告知用户你参考了知识库进行回答"
                }
            )

        response = self.client.chat.completions.create(
            messages=messages,
            model=os.getenv("DEEPSEEK_MODEL"),   # deepseek 模型名，如 "deepseek-chat"
            top_p=0.2,
            stream=True,
            tool_choice="auto",
            tools=self.tools.tools_define()
        )

        # 命中了插件
        for bingoTool, content in self.tools.tool_call_stream(response, messages):
            if bingoTool:
                yield content

        # 正常消息
        if not bingoTool:
            msg = ""
            for one in response:
                chunk = one.choices[0].delta
                if chunk.content is not None:
                    msg += chunk.content
                    yield msg

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
            model=os.getenv("DEEPSEEK_MODEL"),
            top_p=0.2,
            response_format={"type": "json_object"},
            stream=False
        )

        return json.loads(chat_completion.choices[0].message.content)["purpose"]

    def system_role(self):
        return "Dzzzz的智能客服助手"


instance = Service()
