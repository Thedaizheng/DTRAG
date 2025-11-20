import gradio as gr
from rag import chatbot_ui
from rag.service import service
import utils


class Chatbot:
    def generate_ui(self):
        return chatbot_ui.ChatbotUI(self).generate_ui()

    def handle_msg(self, prompt, history, user, doc_group, request: gr.Request):
        for rs in service.instance.handle_user_chat(
            user=user,
            prompt=prompt,
            messages=utils.gradio_history_to_openai_messages(
                history, service.instance.system_role()),
            doc_group=doc_group,
            need_semantic_analysis=True
        ):
            yield rs
