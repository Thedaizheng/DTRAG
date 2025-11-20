import gradio as gr
import threading
import os

css = """
        .gradio-container {
            background-color: #001f3f; /* 深蓝色背景 */
        }
        h1 { 
            color: white !important; /* 标题字体颜色为白色 */
            margin-top: 20px;        /* 增加顶部间距 */
            margin-bottom: 20px;     /* 增加底部间距 */
        }

    """
class ChatbotUI:
    def __init__(self, chatbot):
        self.chatbot = chatbot

    def generate_ui(self):
        with gr.Blocks(css=css) as gr_service:
            gr.Markdown(
                f"<h1 style='text-align: center; margin-bottom: 1rem'>智能客服问答</h1>")

            with gr.Row():
                user = gr.Dropdown(
                    choices=os.getenv("users").split(","),
                    label="用户（模拟）"
                )
                doc_group = gr.Dropdown(
                    choices=os.getenv("doc_groups").split(","),
                    label="Doc Group")

            chatbot = gr.Chatbot([], elem_id="chatbot",
                                 height=500,
                                 bubble_full_width=True)

            with gr.Row():
                msg = gr.Textbox(
                    scale=4,
                    show_label=False,
                    placeholder="请输入你的问题...",
                    container=False,
                    interactive=True,
                )

            with gr.Row():
                gr.ClearButton([chatbot, msg], value="清空")

            msg.submit(
                self._handle_submit,
                [msg, chatbot, user, doc_group], [chatbot, msg], queue=True)

            return gr_service.queue()

    def _handle_submit(self, user_msg, history, user, doc_group, request: gr.Request, *arg):
        history.append([user_msg, ""])

        # 设置默认值
        if user == []:
            user = "用户1"
        if doc_group == []:
            doc_group = "default"

        for rs in self.chatbot.handle_msg(user_msg, history, user, doc_group, request):
            history[-1][1] = rs
            # 生成内容过程中，禁用btn
            yield history, gr.Textbox(interactive=False, value="")

        # 生成完内容，则启用btn
        yield history, gr.Textbox(interactive=True, value="")


