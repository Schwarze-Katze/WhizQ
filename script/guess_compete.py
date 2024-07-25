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
    log_filename = f"log/pattern3_log_{current_time}.txt"
    logging.basicConfig(level=logging.INFO, handlers=[
                        logging.FileHandler(log_filename, 'a', 'utf-8')])
    logging.info("【当前模式】：人和机器竞猜")

    # 处理难度对应猜词范围数，简单难度 5 ，普通难度 10，困难难度 20
    range_num = {
        "简单": 5,
        "普通": 10,
        "困难": 20
    }
    if difficulty not in range_num:
        raise ValueError(f"Invalid difficulty selected.")

    # 创建 WhizQClient 实例
    client = WhizQClient(eb_token, model, temperature, top_p, range_num[difficulty], theme_selected)
    client.model = model
    client.temperature = temperature
    client.top_p = top_p

    # 初始化谜题
    truth, range = client.Initialize_20Q_puzzle()

    # 初始化系统提示
    system_prompt = f"你正在参与“**人机竞猜**”的游戏，主题是“**{theme_selected}**”。在这个游戏中，" \
                    f"你和猜词机器将轮流提问来猜测一个未知的谜题。" \
                    f"在这个过程中，你和猜测机器所提问题以及答案是共享的，" \
                    f"对于所有的问题，会有一个解答机器进行回答。" \
                    f"所有的问题只能是一般疑问句（是非问句）。" \
                    f"谁先猜出正确的谜底，谁就获得本次竞猜的胜利。\n"\
                    f"谜底可能是以下词：{range}"
    
    history = [(None, system_prompt)]

    # 打印初始系统提示词
    print("系统: ", history[0][1])

    return "游戏开始", history, "游戏中", ""

def add_message(history, message, user_turn, state):
    global client
    try:
        # 用户回答
        if "猜对了" in state:
            return history, gr.MultimodalTextbox(value=None, interactive=False), user_turn, state
        else:
            state = "游戏中"
        user_question = message["text"]
        history.append(
            (client.make_html(user_question, "file/assets/human_icon.png"), None))
        print("用户: ", history[-1][0])
        user_turn = True

        # 打印聊天历史记录的最新交互
        print(f"用户提问: {history[-1][0]}")
        return history, gr.MultimodalTextbox(value=None, interactive=False), user_turn, state
    except NameError:
        return history, gr.MultimodalTextbox(value=None, interactive=False), user_turn, state


def update_chat_q(history, state, user_turn, info):
    global client
    try:
        if "猜对了" in state:
            history = history
        else:
            # 生成机器提问
            history = client.query_bot(history, reverse_side=True)
            question = history[-1][0]
            print(f"猜词机器提问: {question}")
            user_turn = False
        return history, state, user_turn, info
    except NameError:
        return history, state, user_turn, info


def update_chat_a(history, state, user_turn, info):
    global client
    try:
        if "猜对了" in state:
            history = history
        else:
            history = client.answer_bot(history)
            print(f"解答机器回复: {history[-1][1]}")
        if "猜对了" in history[-1][1]:
            if user_turn:
                state = "玩家猜对了"
                info = "您已猜对关键词。点击“开始”按钮可重新开始游戏。"
            elif state != "玩家猜对了":
                state = "机器猜对了"
                info = "机器已猜对关键词。点击“开始”按钮可重新开始游戏。"

        if "猜对了" in state:
            history = history
            gr.Info(info)
        return history, state, user_turn, info
    except NameError:
        return history, state, user_turn, info


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