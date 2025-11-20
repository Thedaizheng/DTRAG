import chromadb
import os
from sentence_transformers import SentenceTransformer

# 固定使用 BGE-large-zh-v1.5，缓存到项目目录
embedding_model = "BAAI/bge-large-zh-v1.5"
bge_model = SentenceTransformer(embedding_model, cache_folder=r"E:\DTRAG\models")
dim = bge_model.get_sentence_embedding_dimension()  # 自动获取维度


class DBChroma:
    def __init__(self, collection_name="documents"):
        # 使用 PersistentClient，数据存储到本地
        self.client = chromadb.PersistentClient(path=r"E:\DTRAG\DTRAG_GPT4o_BAAI\rag_db")

        # Chroma v0.6.0: list_collections() 只返回名字
        existing_collections = [c for c in self.client.list_collections()]
        if collection_name in existing_collections:
            self.collection = self.client.get_collection(collection_name)
            # 检查维度是否一致
            coll_dim = self.collection.metadata.get("dimension")
            if coll_dim is not None and coll_dim != dim:
                print(f"⚠️ 维度不一致: collection={coll_dim}, model={dim}")
                print("👉 建议清空旧的 collection 或换成相同维度的模型")
        else:
            # 新建 collection 并记录维度
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine", "dimension": dim}
            )

        self.distance = 0.3

    def _get_embeddings(self, embedding_input):
        # 生成 BGE 向量，并归一化（推荐做法）
        embeddings = bge_model.encode(
            embedding_input,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embeddings.tolist()

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
            include=["metadatas", "documents", "embeddings"]
        )

        print("向量数据库查询结果：", results)  # 🔍 调试用

        if not results or "metadatas" not in results or not results["metadatas"]:
            print("⚠️ 查询结果为空或格式不匹配")
            return []

        doc_nodes_ids = []
        for i, match in enumerate(results["metadatas"][0]):
            if match is not None and isinstance(match, dict):
                metadata = match.get("content", "")
                print(f"🔍 第 {i + 1} 个匹配: {metadata}")
                if match.get("doc_ver_id") in doc_ver_ids:
                    doc_nodes_ids.append(results["ids"][0][i])

        return doc_nodes_ids


def init_db():
    from chromadb import PersistentClient
    client = PersistentClient(path=r"E:\DTRAG\DTRAG_GPT4o_BAAI\rag_db")
    for one in ["documents"]:  # 默认只有 documents
        client.get_or_create_collection(
            name=one,
            metadata={"hnsw:space": "cosine", "dimension": dim}
        )
