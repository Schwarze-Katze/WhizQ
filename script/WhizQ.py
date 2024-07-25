import pandas as pd
import erniebot
import gradio as gr
import logging
import random
from rag_query import RAGQuery

class WhizQClient:
    def __init__(self, token, model, temperature, top_p, range_num, theme):
        # 设置 ErnieBot API 类型和令牌
        if not token or not len(token):
            token = "***"
        self.token = token
        erniebot.api_type = "aistudio"
        erniebot.access_token = self.token
        # 初始化知识库和关键词
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.key_libary = []
        self.selected_key = None
        self.key_responce = None
        self.random_keys_str = None
        self.conversation_count = 0
        self.range_num = range_num
        self.theme = theme
        # 通过用户所选主题选择数据集
        self.theme_datasetname = {
            "星际探秘": "StarExplore",
            "生灵百态": "NatureLife",
            "海古遗迹": "OceanRuins"
        }
        # 主题提示词
        self.theme_prompt = {
            "星际探秘": "天文、航空与航天",
            "生灵百态": "生物、动物与植物",
            "海古遗迹": "海洋与古生物"
        }

    # 函数：调用 ErnieBot 生成聊天回复
    def chat(self, message):
        try:
            response = erniebot.ChatCompletion.create(
                model=self.model,
                messages=message,
                temperature=self.temperature,
                top_p=self.top_p)
            return response.get_result()
        except:
            return "API不可用，请检查API"

    def make_html(self, content, icon):
        return gr.HTML(f"""
            <div style="display: flex; padding: 0px 0px; margin-top: 0px;">
                <div style="padding: 10px; flex-shrink: 0;">
                    <!--CONTENT_BEGIN-->{content}<!--CONTENT_END-->
                </div>
                <div style="flex-shrink: 0; margin: 0px; width: 50px; height: 50px; background-image: url({icon}); background-size: cover; border-radius: 50%;" />
            </div>
        """)

    def extract_content(self, html: gr.HTML):
        html_string = html.value
        # 定位 content 开始的注释
        start = html_string.find("<!--CONTENT_BEGIN-->") + \
            len("<!--CONTENT_BEGIN-->")
        # 定位 content 结束的注释
        end = html_string.find("<!--CONTENT_END-->")
        # 截取并返回 content
        return html_string[start:end].strip()

    # 函数：科普机器人回复
    def education_bot(self):
        
        # 使用 RAG 进行查询
        reference_content = self.search_query(f"{self.theme_datasetname[self.theme]}_knowledge", self.selected_key, k_num=2, return_str=False)
        selected_entry = random.choice(reference_content)  # 从列表中随机选择一个元素
        
        instruction = f"我将提供一段关于{self.theme_prompt[self.theme]}的长文本，请将其处理为一段趣味科普百科文章。" \
                      f"尽可能保留原本的科学内容和信息，同时删去一些不完整或冗长的部分(输出结果不超过150字），使其更加通俗易懂和有趣。" \
                      f"输出的内容不包括标题，以下是文本内容：\n "\
                      f"参考文本的标题是：{selected_entry['query']}，内容如下：{selected_entry['response']}"
        messages = [{"role": "user", "content": instruction}]
        
        self.conversation_count += 1
        logging.info(f"【科普：文心Prompt{self.conversation_count:02d}】 {messages}")
        chatResult = self.chat(messages)
        logging.info(f"【科普：文心Answer{self.conversation_count:02d}】 {chatResult}\n")
        return selected_entry['query'], chatResult


    # 函数：解释机器人回复
    def explain_bot(self, history):
        latest_user_text = history[-1][0]
        if isinstance(latest_user_text, gr.HTML):
            latest_user_text = self.extract_content(latest_user_text)
        
        # 使用 RAG 进行查询
        reference_content1 = self.search_query(f"{self.theme_datasetname[self.theme]}_keypedia", latest_user_text, k_num=2)
        reference_content2 = self.search_query(f"{self.theme_datasetname[self.theme]}_knowledge", latest_user_text, k_num=2)
        
        instruction = f"你是一个解释助手机器人，用户会提出关于“{self.theme_prompt[self.theme]}”的各种问题。" \
                      f"你需要根据知识库中的内容进行解答。问题内容是：\n{latest_user_text}\n"
        messages = [{"role": "user", "content": instruction + "参考内容如下：\n" + reference_content1 + reference_content2}]
        
        self.conversation_count += 1
        logging.info(f"【解释：文心Prompt{self.conversation_count:02d}】 {messages}")
        chatResult = self.chat(messages)
        logging.info(f"【解释：文心Answer{self.conversation_count:02d}】 {chatResult}\n")
        history[-1] = (history[-1][0], chatResult)
        return history

    # 函数：解答机器人回复
    def answer_bot(self, history):

        # 只记录最新的一组对话
        latest_user_text = history[-1][0]
        if isinstance(latest_user_text, gr.HTML):
            latest_user_text = self.extract_content(latest_user_text)

        instruction = f"你是一个猜谜语解答助手机器人，用户将会对关于谜底是“{self.selected_key}”的谜题进行猜测，你负责基于事实给出解答。" \
                      f"假如用户的【回复内容】包含【谜底】“{self.selected_key}”，回复：“猜对了。”。"\
                      f"假如用户的【回复内容】不包含【谜底】“{self.selected_key}”，请根据关于谜底的事实来回答用户的问题。如果用户的关于谜底的【问题】是正确的，回复'是。'，否回复'否。'。"\
                      f"假如用户的【回复内容】和{self.theme_prompt[self.theme]}无关，回复“请提和主题相关的问题。”"\
                      f"不要在回复时透露【谜底】“{self.selected_key}”的多余信息。\n"\
                      f"【谜底】可能是以下词：{self.random_keys_str}"
        messages = [
            {
                "role": "user", "content": 
                instruction + "回答时参考内容：\n" + 
                self.key_responce +
                "用户的【回复】是：\n" + latest_user_text
                }
            ]

        self.conversation_count += 1  # 获取当前对话次数
        logging.info(f"【解答：文心Prompt{self.conversation_count:02d}】 {messages}")
        chatResult = self.chat(messages)
        logging.info(f"【解答：文心Answer{self.conversation_count:02d}】 {chatResult}\n")
        chatResult = chatResult.split('。', 1)[0] + "。"# 截取第一个句号前的内容
        history[-1] = (history[-1][0], chatResult)
        return history
    
    # 函数：猜词机器人提问
    def query_bot(self, history, reverse_side=False):
        self.conversation_count += 1  # 获取当前对话次数

        
        instruction = f"假设你是一个猜谜语机器人，请和我玩一个游戏，我会在心中想一个和'{self.theme_prompt[self.theme]}'有关的名词。"\
                      f"我的回答只会是以下四种之一：'猜对了'、'是'、'否'、'不知道'。你来推测我选择的名词是什么。"\
                      f"尽量用二分法逐步缩小范围，根据【过往对话】推测出谜底，不要重复提问相同的问题。"\
                      f"请参考【过往对话】信息给出一个【一般疑问句】(是非疑问句)，只回答一个问句，不要回答其他内容。\n"\
                      f"请进行充分的思考，要求猜出谜底的速度要快，注意不要重复之前的问题，或问已经能推理出答案的问题，追求速度不追求准确性。"\
                      f"【谜底】可能是以下词：{self.random_keys_str}"

        # 将 history 转换为 messages 格式
        messages = [
            {
                'role': 'user', 'content': 
                instruction
                }
            ]
        for i, (user_text, assistant_text) in enumerate(history[2:], start=2):
            if isinstance(user_text, gr.HTML):
                user_text = self.extract_content(user_text)
            if isinstance(assistant_text, gr.HTML):
                assistant_text = self.extract_content(assistant_text)
            if reverse_side:
                messages.append({"role": "assistant", "content": user_text})
                messages.append({"role": "user", "content": assistant_text if assistant_text is not None else ""})
            else:
                if i % 2 == 0:
                    messages.append({"role": "assistant", "content": assistant_text})
                else:
                    messages.append({"role": "user", "content": user_text})

        # 确保 messages 的最后一个成员为当前请求的信息
        if len(messages) % 2 == 0:
            messages.pop()

        logging.info(f"【猜词：文心Prompt{self.conversation_count:02d}】 {messages}")
        chatResult = self.chat(messages)
        logging.info(f"【猜词：文心Question{self.conversation_count:02d}】 {chatResult}\n")
        if reverse_side:
            history.append(
                (self.make_html(chatResult, "file/assets/robot_icon.jpg"), None))
        else:
            history.append((None, chatResult))
        return history

    # 函数：从key库中随机选择一个关键词
    def select_keyword(self):
        self.selected_key = random.choice(self.key_libary)
        self.random_keys_str = self.random_keys_with_selected(self.selected_key, self.range_num)
        logging.info(f"【选择的谜底】{self.selected_key}")
        logging.info(f"【谜底的范围】{self.random_keys_str}")
        return self.selected_key, self.random_keys_str

    # 函数：生成随机的猜词范围
    def random_keys_with_selected(self, selected_key, num=10):
        # 检查请求的key的数量是否超过知识库的大小
        if num > len(self.key_libary):
            raise ValueError("请求的键的数量超过了知识库的大小。")

        keys = self.key_libary.copy()
        keys.remove(selected_key)  # 移除 selected_key
        random_keys = random.sample(keys, num - 1)  # 随机选择 (num - 1) 个key
        random_keys.append(selected_key)  # 添加 selected_key
        random.shuffle(random_keys)  # 打乱顺序
        random_keys_str = "**" + "**；**".join(random_keys) + "**。"  # 转换为字符串
        return random_keys_str
    
    # 函数：调用 RAGQuery 进行查询，得到参考回答
    def search_query(self, databasename, query, k_num=4, return_str=True):
        rag_client = RAGQuery(databasename, erniebot_access_token=self.token)
        response = rag_client.search(query, k=k_num)
        if return_str:
            response_str = [f"{item['response']}" for item in response]
            return response_str[0]
        else:
            return response

    # 函数：初始化20Q谜题
    def Initialize_20Q_puzzle(self):
        # 生成文件路径，读取数据
        file_path = f"data/{self.theme_datasetname[self.theme]}_keypedia.xlsx"
        data = pd.read_excel(file_path)
        # 将数据转换为列表
        self.key_libary = list(data['keyword'])

        chosen_keyword, random_keys_str = self.select_keyword()
        self.key_responce = self.search_query(f"{self.theme_datasetname[self.theme]}_keypedia", self.selected_key, k_num=1)
        logging.info(f"【选择词的百科】{self.key_responce}")
        return chosen_keyword, random_keys_str