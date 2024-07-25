import gradio as gr
import time
import logging
from WhizQ import WhizQClient

client: WhizQClient

def init_model(eb_token, model, theme_selected, difficulty, temperature, top_p):
    global client

    # 配置日志记录
    # 清理已有 handlers
    root_logger = logging.getLogger()
    for h in root_logger.handlers:
        root_logger.removeHandler(h)
    current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"log/pattern1_log_{current_time}.txt"
    logging.basicConfig(level=logging.INFO, handlers=[
                        logging.FileHandler(log_filename, 'a', 'utf-8')])
    logging.info("【当前模式】：机器猜人回答")

    # 处理难度对应猜词范围数，简单难度 5 ，普通难度 10，困难难度 20
    range_num = {
        "简单": 5,
        "普通": 10,
        "困难": 20
    }
    if difficulty not in range_num:
        raise ValueError("Invalid difficulty selected.")

    # 创建 WhizQClient 实例
    client = WhizQClient(eb_token, model, temperature, top_p, range_num[difficulty], theme_selected)
    client.model = model
    client.temperature = temperature
    client.top_p = top_p

    # 初始化谜题
    truth, range = client.Initialize_20Q_puzzle()


    # 初始化系统提示
    system_prompt = f"你正在参与“**用户猜谜**”模式的20Q游戏，主题是“**{theme_selected}**”。在这个游戏中，机器已经选择了一个词，"\
                    f"你需要通过提问来猜测这个词。每次提问后，机器将根据你的问题给出回答。请开始你的提问吧！\n"\
                    f"谜底可能是以下词：{range}"
    
    history = [(None, system_prompt)]

    # 打印初始系统提示词
    print("系统: ", history[0][1])
    
    return "游戏开始", history, "游戏中", ""

def add_message(history, message, state):
    global client
    try:
        client
    except NameError:
        return history, gr.MultimodalTextbox(value=None, interactive=False), state
    # 用户回答
    if "猜对了" in state:
        return history, gr.MultimodalTextbox(value=None, interactive=False), state
    else:
        state = "游戏中"
    user_answer = message["text"]
    history.append((user_answer, None))
    print("用户: ", history[-1][0])
    return history, gr.MultimodalTextbox(value=None, interactive=False), state


def update_chat(history, state, info):
    global client
    try:
        history = client.answer_bot(history)
        print("机器人: ", history[-1][1])
        if "猜对了" in history[-1][1]:
            state = "猜对了"

        if state == "猜对了":
            history = history
            info = "您已猜对关键词。点击“开始”按钮可重新开始游戏。"
            gr.Info("您已猜对关键词。点击“开始”按钮可重新开始游戏。")
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


def show_extend_read(extend_read, state):
    if '猜对了' in state:
        title, comment = client.education_bot()
        extend_read = f"""### 谜底百科：{client.selected_key}\n\n
                          {client.key_responce}\n\n
                          ### 拓展阅读：{title}\n\n
                          {comment}
                      """
    return extend_read
