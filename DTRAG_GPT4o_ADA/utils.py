from gradio import Request
import base64


def gradio_history_to_openai_messages(history, system_role=""):
    openai_messages = []
    if system_role != "":
        openai_messages.append({
            "role": "system",
            "content": system_role
        })

    for one in history:
        if one[0] == '' or one[1] == '':
            continue

        openai_messages.append({
            "role": "user",
            "content": one[0],
        })

        openai_messages.append({
            "role": "assistant",
            "content": one[1],
        })

    return openai_messages


def get_gpt_chunk_tool_calls(chunk):
    return chunk.choices[0].delta.tool_calls


def save_file_by_content(chatbot_name, file_name, content):
    file_path = f"/static/{chatbot_name}_{file_name}"
    with open("."+file_path, 'wb') as file:
        file.write(content)

    return file_path


def create_file_url_path(req: Request, file_path: str):
    return req.request.base_url._url[:-1] + file_path


def chat_with_img(history):
    if len(history) < 2 or not isinstance(history[-2][0], tuple) or len(history[-2][0]) < 1 or history[-2][1] is not None:
        return None

    with open(history[-2][0][0], "rb") as image_file:
        binary_data = image_file.read()

    return base64.b64encode(binary_data).decode('utf-8')
