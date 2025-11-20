import chromadb
import os
import openai

gpt_model = "text-embedding-ada-002"
dim = 1536


class DBChroma:
    def __init__(self):
        # 改为使用 PersistentClient 或默认 Client
        self.client = chromadb.PersistentClient(path=r"E:\DTRAG\DTRAG_GPT4o_ADA\rag_db")  # 移除 path 参数
        self.collection = self.client.get_or_create_collection(name="documents", metadata={"hnsw:space": "cosine"})
        self.distance = 0.3

    def _get_embeddings(self, embedding_input):
        client = openai.OpenAI(base_url = "http://chatapi.littlewheat.com/v1",api_key=os.getenv("api_key"))
        embeddings = client.embeddings.create(
            model=gpt_model,
            input=embedding_input,
        )
        return [i.embedding for i in embeddings.data]

    def add_doc(self, doc_group, doc_formatted, doc_nodes_ids, doc_ver_ids):
        embeddings = self._get_embeddings([doc['content'] for doc in doc_formatted])
        for doc, embedding, node_id, ver_id in zip(doc_formatted, embeddings, doc_nodes_ids, doc_ver_ids):
            self.collection.add(
                ids=[str(node_id)],
                embeddings=[embedding],
                metadatas=[{"doc_ver_id": ver_id, "content": doc['content']}]
            )

    def search(self, doc_group, query, doc_ver_ids, limit=5):
        query_embedding = self._get_embeddings([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["metadatas", "documents", "embeddings"]  # 确保返回 metadata
        )

        print("向量数据库查询结果：", results)  # 🔍 打印调试

        if not results or "metadatas" not in results or not results["metadatas"]:
            print("⚠️ 查询结果为空或格式不匹配")
            return []

        doc_nodes_ids = []
        for i, match in enumerate(results["metadatas"][0]):  # ✅ 确保索引正确
            if match is not None and isinstance(match, dict):  # ✅ 过滤 None
                metadata = match.get("content", "")  # 直接获取 content
                print(f"🔍 第 {i + 1} 个匹配: {metadata}")
                if match.get("doc_ver_id") in doc_ver_ids:
                    doc_nodes_ids.append(results["ids"][0][i])

        return doc_nodes_ids


def init_db():
    from chromadb import PersistentClient
    client = PersistentClient(path=r"E:\DTRAG\DTRAG_GPT4o_ADA\rag_db")  # 指定存储路径
    for one in os.getenv("doc_groups").split(","):
        client.get_or_create_collection(name=one, metadata={"hnsw:space": "cosine"})

