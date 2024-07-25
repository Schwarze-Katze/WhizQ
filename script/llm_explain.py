import gradio as gr
import time
import logging
from WhizQ import WhizQClient

client: WhizQClient

def init_model(eb_token, model, theme_selected, temperature, top_p):
    global client

    # 配置日志记录
    # 清理已有 handlers
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        root_logger.removeHandler(h)
    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"log/pattern0_log_{current_time}.txt"
    logging.basicConfig(level=logging.INFO, handlers=[
                        logging.FileHandler(log_filename, 'a', 'utf-8')])
    logging.info("【当前模式】：解释机器人")

    # 创建 WhizQClient 实例
    client = WhizQClient(eb_token, model, temperature, top_p, 10, theme_selected)
    client.model = model
    client.temperature = temperature
    client.top_p = top_p

    # 初始化系统提示
    system_prompt = f"你正在与问答科普机器人对话，主题是“**{theme_selected}**”。请提出你的问题，机器人将根据知识库进行解答。"

    history = [(None, system_prompt)]

    # 打印初始系统提示词
    print("系统: ", history[0][1])
    
    return "对话开始", history


def add_message(history, message):
    global client
    try:
        client
    except NameError:
        return history, gr.MultimodalTextbox(value=None, interactive=False)
    # 用户提问
    user_question = message["text"]
    history.append((user_question, None))
    print("用户: ", history[-1][0])
    return history, gr.MultimodalTextbox(value=None, interactive=False)

def update_chat(history, state, info):
    global client
    try:
        history = client.explain_bot(history)
        print("机器人: ", history[-1][1])
        return history, state, info
    except NameError:
        return history, state, info


def change_llm_parameter(temperature, top_p):
    global client
    try:
        client.temperature = temperature
        client.top_p = top_p
    except NameError:
        return

if __name__ == "__main__":
    # Example usage
    eb_token = ""
    model = "ernie-bot-4"
    theme_selected = "星际探秘"  # Example theme
    temperature = 0.7
    top_p = 0.9

    state, history = init_model(eb_token, model, theme_selected, temperature, top_p)

    while True:
        user_input = input("用户: ")
        if user_input.lower() in ["退出", "exit", "quit"]:
            break
        message = {"text": user_input}
        history, _ = add_message(history, message)
        history, state, info = update_chat(history, state, "")
        print("机器人: ", history[-1][1])
