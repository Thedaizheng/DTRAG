# import json
# from rag.kdb.doc_handler import base
# import openai
# import os
#
#
# class Formatter(base.BaseDocHandler):
#     def run(self, sess: base.Session):
#         if sess.text == "":
#             return
#
#         client = openai.OpenAI(api_key=os.getenv("api_key"))
#         chat_completion = client.chat.completions.create(
#             messages=[{
#                 "role": "user",
#                 "content": self.get_prompt(sess.text)
#             }],
#             model=os.getenv("gpt_model"),
#             stream=False,
#             response_format={"type": "json_object"}
#         )
#
#         rs = json.loads(chat_completion.choices[0].message.content)
#         print(rs)
#         for one in rs["data"]:
#             phones = one.get("phone")
#             # 判断是否有需要处理的敏感手机号
#             if phones is not None and len(phones) > 0:
#                 for one_phone in phones:
#                     one["content"] = one["content"].replace(
#                         one_phone, self.mask_phone_number(one_phone))
#
#         sess.text_formatted = rs["data"]
#
#     def mask_phone_number(self, phone):
#         masked_phone = phone[:3] + "****" + phone[7:]
#         return masked_phone
#
#     def get_prompt(self, content):
#         response_format = {
#             "data": [
#                 {
#                     "id": "int型，唯一ID",
#                     "level": "int型，层级",
#                     "parent_id": "int型，父节点id，如果没有父节点则取值-1",
#                     "seq_index": "int型，如果是同一层级且同一父级，则该代表语句顺序index，从1开始",
#                     "content": "内容",
#                     "phone": "数组，文本中出现的手机号"
#                 }
#             ]
#         }
#
#         response_format_str = json.dumps(response_format)
#
#         return f'''
# # Role
# - 你是一个文档处理助手，你需要按照文档含义将文档分成父子结构
# ## Attention
# - 只引用内容，不要改变文档的内容
# - 分层后的内容的合集对比原始文本，不要出现文本丢失
# ## WorkFlow
# - 先按照语义将文档进行分段，每段内容语义要内聚
# - 在基于分段的内容进行从属关系的划分
# - 找到段落中可能会出现的手机号并标识出来
# - 文本中的所有文字都要被分为父子结构，不要遗漏任何的文字
# - 请仅输出标准 JSON 格式，确保所有属性名用双引号 " 包裹，无需添加其他说明。
# ## Task
# - 分析 """{content}"""
# ## JSON
# - """{response_format_str}"""
# ## Init
# - 做为<Role>，严格遵守<Attention>，并依照<WorkFlow>去完成<Task>，并以<JSON>方式输出
# '''


import json
import re
import os
import json5
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from rag.kdb.doc_handler import base


class Formatter(base.BaseDocHandler):
    def run(self, sess: base.Session):
        """
        主流程：
        1. 使用 OpenAI 模型进行语义分块；
        2. 自动识别手机号并脱敏；
        3. 构建层次结构；
        4. 输出标准结构化 JSON。
        """
        if not sess.text:
            print("⚠️ 无输入文本，跳过处理。")
            return

        # ===== Step 1: 调用 OpenAI 模型分块 =====
        client = OpenAI(base_url = "http://chatapi.littlewheat.com/v1",api_key=os.getenv("api_key"))
        print("🧠 正在调用 OpenAI 模型进行语义分块 ...")

        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": self.get_prompt(sess.text)}],
            model=os.getenv("gpt_model"),
            stream=False,
            response_format={"type": "json_object"}
        )

        raw_content = chat_completion.choices[0].message.content.strip()
        rs = self._clean_json(raw_content)
        blocks = rs.get("data", [])
        if not blocks:
            raise ValueError("⚠️ 模型未返回有效 data 数据")

        print(f"✅ 模型语义分块完成，共 {len(blocks)} 个语义块。")

        # ===== Step 2: 手机号脱敏 =====
        for one in blocks:
            phones = one.get("phone", [])
            if phones:
                for phone in phones:
                    one["content"] = one["content"].replace(
                        phone, self.mask_phone_number(phone)
                    )

        # ===== Step 3: 构建层次树结构 =====
        tree_data = self._build_tree(blocks)
        sess.text_formatted = tree_data
        print("🎯 文档格式化完成！")

    # =========================================================
    #   层次聚类构建树
    # =========================================================
    def _build_tree(self, blocks):
        """
        使用 SentenceTransformer + 层次聚类构建树状结构。
        """
        model_path = r"E:\DTRAG\models\bge-large-zh-v1.5"
        model = self._ensure_local_bge_model(model_path)

        texts = [b["content"] for b in blocks if b.get("content")]
        if not texts:
            raise ValueError("❌ 无有效文本块内容！")

        print("🔍 正在生成文本 embedding ...")
        embeddings = model.encode(texts, normalize_embeddings=True)
        sim_matrix = cosine_similarity(embeddings)
        distance_matrix = 1 - sim_matrix

        print("🌳 正在执行层次聚类 ...")
        try:
            clustering = AgglomerativeClustering(
                metric="precomputed",
                linkage="average",
                distance_threshold=0.3,
                n_clusters=None
            )
            clustering.fit(distance_matrix)
        except Exception as e:
            print(f"⚠️ 聚类失败，使用线性层级回退。错误: {e}")
            clustering = None

        # ===== 生成树节点 =====
        nodes = []
        next_id = 1
        for i, blk in enumerate(blocks):
            nodes.append({
                "id": next_id,
                "level": blk.get("level", 1),
                "parent_id": blk.get("parent_id", -1),
                "seq_index": blk.get("seq_index", i + 1),
                "content": blk.get("content", ""),
                "phone": blk.get("phone", [])
            })
            next_id += 1

        if clustering is None:
            return nodes

        labels = clustering.labels_
        cluster_dict = {}
        for idx, label in enumerate(labels):
            cluster_dict.setdefault(label, []).append(idx)

        cluster_ids = sorted(cluster_dict.keys())
        for cluster_id in cluster_ids:
            child_indices = cluster_dict[cluster_id]
            if len(child_indices) <= 1:
                continue

            parent_idx = child_indices[0]
            parent_node = nodes[parent_idx]
            parent_node["level"] = 1
            parent_node["parent_id"] = -1

            for j, child_idx in enumerate(child_indices[1:], start=1):
                nodes[child_idx]["level"] = 2
                nodes[child_idx]["parent_id"] = parent_node["id"]
                nodes[child_idx]["seq_index"] = j

        print(f"✅ 层次树构建完成，共 {len(nodes)} 个节点。")
        return nodes

    # =========================================================
    #   自动检测并下载本地 BGE 模型
    # =========================================================
    def _ensure_local_bge_model(self, model_path: str):
        """
        检查本地模型路径，如果不存在则自动下载到该目录。
        """
        if not os.path.exists(model_path):
            print("⚙️ 检测到本地模型不存在，正在从 HuggingFace 下载……")
            model = SentenceTransformer("BAAI/bge-large-zh-v1.5")
            os.makedirs(model_path, exist_ok=True)
            model.save(model_path)
            print(f"✅ 模型已下载并保存至: {model_path}")
        else:
            print(f"✅ 检测到本地模型，直接加载: {model_path}")
            model = SentenceTransformer(model_path)
        return model

    # =========================================================
    #   稳健 JSON 解析（支持 JSON5 / Markdown 包裹）
    # =========================================================
    def _clean_json(self, raw_content: str) -> dict:
        for loader in (json, json5):
            try:
                return loader.loads(raw_content)
            except Exception:
                pass

        cleaned = re.sub(r"^```[a-zA-Z]*", "", raw_content)
        cleaned = re.sub(r"```$", "", cleaned)
        cleaned = cleaned.strip()

        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            json_str = match.group(0)
            for loader in (json, json5):
                try:
                    return loader.loads(json_str)
                except Exception:
                    continue

        path = os.path.join(os.getcwd(), "debug_raw_output.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(raw_content)
        raise ValueError(f"❌ JSON解析失败，原始输出已保存至: {path}")

    # =========================================================
    #   手机号脱敏
    # =========================================================
    def mask_phone_number(self, phone: str) -> str:
        if len(phone) >= 11:
            return phone[:3] + "****" + phone[7:]
        return phone

    # =========================================================
    #   提示词构造
    # =========================================================
    def get_prompt(self, content: str) -> str:
        response_format = {
            "data": [
                {
                    "id": "int型，唯一ID",
                    "level": "int型，层级",
                    "parent_id": "int型，父节点id，如果没有父节点则取值-1",
                    "seq_index": "int型，同层级顺序，从1开始",
                    "content": "内容",
                    "phone": "数组，文本中出现的手机号"
                }
            ]
        }

        response_format_str = json.dumps(response_format, ensure_ascii=False)
        return f'''
你是一个文档结构化助手，请根据语义对以下文本进行分段和分层。
要求：
1. 所有内容都必须被划分到一个节点中，不得遗漏；
2. 按语义层级组织，父子层关系清晰；
3. 检测并提取所有手机号；
4. 严格输出标准 JSON，无其他说明文字。

输出格式：
{response_format_str}

文档内容如下：
{content}
'''
