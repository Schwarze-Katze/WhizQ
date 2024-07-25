import numpy as np
import lancedb
import erniebot

class RAGQuery:
    def __init__(self, databasename='StarExplore', erniebot_access_token=None):
        self.databasename = databasename
        self.erniebot_api_type = "aistudio"
        self.erniebot_access_token = erniebot_access_token
        self.uri = "data/sample_lancedb"
        self.db = lancedb.connect(self.uri)
        
        # 设置ErnieBot API
        erniebot.api_type = self.erniebot_api_type
        erniebot.access_token = self.erniebot_access_token

    def embedding(self, query):
        # 生成文本嵌入
        try:
            response = erniebot.Embedding.create(
                model="ernie-text-embedding",
                input=[query])
            return np.asarray(response.get_result()[0])
        except:
            return np.zeros([384])

    def search(self, query, k=4):
        query_vector = self.embedding(query)
        tbl_data = self.db.open_table(f"{self.databasename}")
        results = tbl_data.search(query_vector).limit(k).to_list()
        result_dict = [{'query': d['query'], 'response': d['response']} for d in results]
        return result_dict

# 使用示例
if __name__ == "__main__":
    client = RAGQuery(databasename="StarExplore_knowledge")
    query = "什么是嫦娥一号"
    results = client.search(query, k=4)
    print(results)
