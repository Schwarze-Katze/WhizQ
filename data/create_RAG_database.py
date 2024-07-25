import os
import numpy as np
import pandas as pd
from tqdm import tqdm
import lancedb
import erniebot
import time
import pyarrow as pa
from tenacity import retry, stop_after_attempt, wait_fixed

# 设置ErnieBot API
erniebot.api_type = "aistudio"
erniebot.access_token = "***"
uri = "data/sample_lancedb"
db = lancedb.connect(uri)

def embedding(query):
    # 生成文本嵌入
    response = erniebot.Embedding.create(
        model="ernie-text-embedding",
        input=[query])
    return np.asarray(response.get_result()[0])

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def embedding_with_retry(query):
    time.sleep(0.5)
    return embedding(query)  # 假设这是调用外部服务生成文本嵌入的函数

class ExcelDataset:
    def __init__(self, file_path):
        self.data = []
        df = pd.read_excel(file_path)
        for _, row in df.iterrows():
            self.data.append({'query': row[0], 'response': row[1]})

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]

    def querys(self):
        return [entry['query'] for entry in self.data]

    def get_response(self, query):
        for entry in self.data:
            if entry['query'] == query:
                return entry['response']
        return None

def create_and_populate_table(db, file_path):
    # 提取文件名（不包括扩展名）
    datasetname, _ = os.path.splitext(os.path.basename(file_path))

    # 创建数据表并添加数据
    # 定义数据表结构
    data_schema = pa.schema([
        ("query", pa.string()),
        ("response", pa.string()),
        ("vector", pa.list_(pa.float32(), 384))  # 假设嵌入维度为384
    ])

    # 检查表是否存在
    if not os.path.exists(f"data/sample_lancedb/{datasetname}.lance"):
        tbl_data = db.create_table(f"{datasetname}", schema=data_schema)
    else:
        tbl_data = db.open_table(f"{datasetname}")

    # 加载 Excel 数据集
    dataset = ExcelDataset(file_path)

    # 生成嵌入并存储到数据库
    data_entries = []
    for idx, item in tqdm(enumerate(dataset), total=len(dataset)):
        query = item['query']
        response = item['response']
        try:
            vector = embedding_with_retry(query)  # 使用重试逻辑的嵌入函数
        except Exception as e:
            print(f"尝试生成文本嵌入失败，跳过索引 {idx}: {e}")
            continue
        time.sleep(0.5)

        data_entry = {
            "id": idx,
            "query": query,
            "response": response,
            "vector": vector.tolist()  # 转换为列表以便存储
        }
        data_entries.append(data_entry)

    # 将所有数据添加到表中
    df_data = pd.DataFrame(data_entries)
    tbl_data.add(df_data)
    return tbl_data

def main():
    file_path = 'data/StarExplore.xlsx'
    tbl_data = create_and_populate_table(db, file_path)

    # 查询示例
    query_vector = embedding("什么是地球")
    k = 10
    results = tbl_data.search(query_vector).limit(k).to_list()
    print(results)

if __name__ == "__main__":
    main()
