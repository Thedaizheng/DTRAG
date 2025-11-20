from rag.tools.tool_order import ToolOrder
import json
import openai
import os


class Tools:
    def __init__(self):
        self.tools = [ToolOrder]
        self.client = openai.OpenAI(api_key=os.getenv("api_key"))

    def tool_call_stream(self, chunk, messages):
        first_chunk = next(chunk)
        tool_calls = first_chunk.choices[0].delta.tool_calls
        if tool_calls is None:
            yield False, ""
            return

        # 完成调用tool的过程
        messages.append(first_chunk.choices[0].delta)

        # 等待stream方式的tool call的参数被完整获取
        tool_calls_args = [None for _ in range(len(tool_calls))]
        for other in chunk:
            chunk_tool_calls = other.choices[0].delta.tool_calls
            if chunk_tool_calls is None:
                break

            for i, chunk_tool_call in enumerate(chunk_tool_calls):
                if tool_calls_args[i] is None:
                    tool_calls_args[i] = chunk_tool_call
                    tool_calls_args[i].id = tool_calls[i].id
                    tool_calls_args[i].function.name = tool_calls[i].function.name
                else:
                    tool_calls_args[i].function.arguments += chunk_tool_call.function.arguments

        yield True, self._tool_exec_and_second_req(messages, tool_calls_args)

    def _tool_exec_and_second_req(self, messages, tool_calls):
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            # 获取tool的参数
            tool_args = tool_call.function.arguments

            bingo_tool = None
            for one in self.tools:
                if one.bingo_tool(tool_name):
                    bingo_tool = one.tool_load(tool_args, tool_call.id)
                    break
            if bingo_tool is None:
                continue

            # 执行，并加入上下文
            messages.append({
                "role": "tool",
                "content": json.dumps(bingo_tool.exec()),
                "tool_call_id": bingo_tool.toolCallID
            })

        # 二次请求
        tool_chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=os.getenv("gpt_model"),
            top_p=0.2,
            stream=False,
            tools=self.tools_define(),
            tool_choice="auto"
        )

        messages.append(tool_chat_completion.choices[0].message)

        return tool_chat_completion.choices[0].message.content

    def tool_call(self, response, messages):
        response = response.choices[0].message
        if response.tool_calls is None:
            return False, ""

        messages.append(response)

        return True, self._tool_exec_and_second_req(messages, response.tool_calls)

    def tools_define(self):
        tools = []
        for tool in self.tools:
            tools.append(tool.tool_define())

        return tools
