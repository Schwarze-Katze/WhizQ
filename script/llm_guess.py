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
    log_filename = f"log/pattern2_log_{current_time}.txt"
    logging.basicConfig(level=logging.INFO, handlers=[
                        logging.FileHandler(log_filename, 'a', 'utf-8')])
    logging.info("【当前模式】：人猜机器回答")

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
    state = "游戏中"

    # 初始化系统提示
    system_prompt = f"你正在参与“**AI猜谜**”模式的20Q游戏，主题是“**{theme_selected}**”。在这个游戏中，被选择的谜底是“**{truth}**”，"\
                    f"接下来，机器会通过问问题的方式来猜测这个词。\n"\
                    f"你的回答只能是以下四种之一：'猜对了'、'是'、'否'、'不知道'。"\
                    f"请准备好，并根据机器的提问给予准确的回答。\n"\
                    f"谜底可能是以下词：{range}"
    
    history = [(None, system_prompt), (None, None)]

    # 打印初始系统提示词
    print("系统: ", history[0][1])

    history = client.query_bot(history)
    return "游戏开始", history, state, ""


def add_message(history, message, state):
    global client
    try:
        client
    except NameError:
        return history, state
    # 用户回答
    state = "游戏中"
    user_answer = message
    if user_answer not in ['猜对了', '是', '否', '不知道']:
        gr.Warning("无效的回答，请使用指定的回答格式：'猜对了'、'是'、'否'、'不知道'")
    else:
        history.append((user_answer, None))
        print("用户: ", history[-1][0])

        # 如果用户回答了"猜对了"，结束
        if user_answer == "猜对了":
            state = "猜对了"
            logging.info("机器猜对了关键词")
            gr.Info("机器猜对了关键词。点击“开始”按钮可重新开始游戏。")
    return history, state


def update_chat(history, state, info):
    global client
    try:
        if state == "猜对了":
            history = history
            info = "机器猜对了关键词。点击“开始”按钮可重新开始游戏。"
        else:
            # 生成机器提问
            history = client.query_bot(history)
            print("机器人: ", history[-1][1])
        return history, info
    except NameError:
        return history, info


def toggle_button_state(state, button_1, button_2, button_3, button_4,):
    if state=="猜对了":
        return gr.Button(value="是", interactive=False), gr.Button(value="否", interactive=False), gr.Button(value="不知道", interactive=False), gr.Button(value="猜对了", interactive=False)
    else:
        return gr.Button(value="是", interactive=True), gr.Button(value="否", interactive=True), gr.Button(value="不知道", interactive=True), gr.Button(value="猜对了", interactive=True)


def change_llm_parameter(temperature, top_p):
    global client
    try:
        client.temperature = temperature
        client.top_p = top_p
    except NameError:
        return

def show_extend_read(extend_read, state):
    global client
    try:
        if '猜对了' in state:
            title, comment = client.education_bot()
            extend_read = f"""### 谜底百科：{client.selected_key}\n\n
                            {client.key_responce}\n\n
                            ### 拓展阅读：{title}\n\n
                            {comment}
                        """
        return extend_read
    except NameError:
        return extend_read