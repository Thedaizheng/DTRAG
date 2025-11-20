import chromadb

# 连接 ChromaDB
client = chromadb.PersistentClient()

# 获取所有集合名称
collections = client.list_collections()
print("数据库中的集合列表：")
for name in collections:
    print(f"- {name}")

# 检查 documents 集合是否存在
if "documents" in collections:
    collection = client.get_collection(name="documents")

    # 查看集合中的数据数量
    count = collection.count()
    print(f"\n集合 'documents' 中共有 {count} 条数据")

    # 查看部分数据
    if count > 0:
        peek_data = collection.peek()  # 默认返回 10 条
        print("\n示例数据：")
        print(peek_data)
else:
    print("\n'documents' 集合不存在，请检查数据库是否正确初始化！")
