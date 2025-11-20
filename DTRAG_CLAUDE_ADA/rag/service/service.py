import os
from anthropic import Anthropic  # 使用 Anthropic 官方 SDK
import copy
import json
from rag.kdb.query import query
from rag.tools.tools import Tools
from dotenv import load_dotenv

load_dotenv()


class Service:
    def __init__(self):
        # 使用 Claude 的 api_key
        self.client = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")  # 环境变量名改为 ANTHROPIC_API_KEY
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

        # 构建 Claude 格式的消息
        claude_messages = self._convert_to_claude_messages(messages, prompt, rs)

        # 调用 Claude API
        response = self.client.messages.create(
            model=os.getenv("CLAUDE_MODEL"),  # 如 "claude-3-sonnet-20240229"
            max_tokens=4096,
            temperature=0.2,  # 相当于 top_p=0.2
            messages=claude_messages,
            stream=True
        )

        # Claude 的流式响应处理
        msg = ""
        for chunk in response:
            if chunk.type == 'content_block_delta':
                if chunk.delta.text is not None:
                    msg += chunk.delta.text
                    yield msg

    def semantic_analysis_user_prompt(self, prompt, messages):
        if len(messages) < 2:
            return prompt

        # 转换为 Claude 格式的消息
        claude_messages = self._convert_to_claude_messages(messages, prompt, "")

        # 添加系统提示词
        system_prompt = '''请你基于上下文理解一下用户输入的问题，然后输出用户真正想问的问题，并以json的格式返回，json格式：{"purpose":""}'''

        response = self.client.messages.create(
            model=os.getenv("CLAUDE_MODEL"),
            max_tokens=1024,
            temperature=0.2,
            system=system_prompt,
            messages=claude_messages
        )

        # 解析响应
        response_text = response.content[0].text
        try:
            return json.loads(response_text)["purpose"]
        except:
            return prompt

    def _convert_to_claude_messages(self, messages, current_prompt, knowledge_base_result):
        """将通用消息格式转换为 Claude 格式"""
        claude_messages = []

        for msg in messages:
            if msg["role"] == "user":
                claude_messages.append({
                    "role": "user",
                    "content": msg["content"]
                })
            elif msg["role"] == "assistant":
                claude_messages.append({
                    "role": "assistant",
                    "content": msg["content"]
                })

        # 添加当前消息
        if knowledge_base_result:
            content = f"请参考知识库：'''{knowledge_base_result}'''，回答用户的问题'''{current_prompt}'''，不要告知用户你参考了知识库进行回答"
        else:
            content = current_prompt

        claude_messages.append({
            "role": "user",
            "content": content
        })

        return claude_messages

    def system_role(self):
        return "Dzzzz的智能客服助手"


instance = Service()