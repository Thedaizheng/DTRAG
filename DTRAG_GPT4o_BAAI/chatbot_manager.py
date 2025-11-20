import gradio as gr
from dotenv import load_dotenv
import sys
import importlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import warnings

warnings.filterwarnings("ignore")


class ChatbotManager:
    def __init__(self):
        load_dotenv()
        self.app = FastAPI()
        self.chatbot = self._chatbot_loader()
        self._init_download_folder()
        self._init_chatbot_ui()

    def start(self):
        import uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=int(os.getenv("port")))

    def _init_download_folder(self):
        self.app.mount(
            "/static", StaticFiles(directory="static"), name="static")

    def _init_chatbot_ui(self):
        gr.mount_gradio_app(
            self.app, self.chatbot.generate_ui(), path="/")

    def _chatbot_loader(self):
        chatbot_name = "rag"
        if len(sys.argv) > 1:
            chatbot_name = sys.argv[1]
        chatbot_module = importlib.import_module(f"{chatbot_name}.chatbot")
        chatbot = chatbot_module.Chatbot()
        return chatbot


if __name__ == "__main__":
    chatbot_manager = ChatbotManager()
    chatbot_manager.start()


