# import json
# import re
# import os
# import json5   # ✅ 新增：宽松 JSON 解析
# from rag.kdb.doc_handler import base
# from openai import OpenAI
#
#
# class Formatter(base.BaseDocHandler):
#     def run(self, sess: base.Session):
#         if not sess.text:
#             return
#
#         client = OpenAI(
#             api_key=os.getenv("DEEPSEEK_API_KEY"),
#             base_url="https://api.deepseek.com"
#         )
#
#         chat_completion = client.chat.completions.create(
#             messages=[{"role": "user", "content": self.get_prompt(sess.text)}],
#             model=os.getenv("DEEPSEEK_MODEL"),
#             stream=False,
#             response_format={"type": "json_object"}  # ✅ 尽量要求 JSON
#         )
#
#         raw_content = chat_completion.choices[0].message.content.strip()
#
#         # ======= 清洗 JSON =======
#         rs = self._clean_json(raw_content)
#
#         # ======= 手机号脱敏 =======
#         for one in rs.get("data", []):
#             phones = one.get("phone")
#             if phones:
#                 for one_phone in phones:
#                     one["content"] = one["content"].replace(
#                         one_phone, self.mask_phone_number(one_phone)
#                     )
#
#         sess.text_formatted = rs["data"]
#
#     # =========================================================
#     #   JSON 解析增强版
#     # =========================================================
#     def _clean_json(self, raw_content: str) -> dict:
#         """
#         稳健 JSON 解析流程：
#         1. 尝试标准 json.loads
#         2. 尝试 json5.loads
#         3. 清洗 markdown/代码块 + 正则提取 {...}
#         4. 再次用 json/json5 尝试
#         """
#         # Step 1: 直接尝试标准 JSON
#         try:
#             return json.loads(raw_content)
#         except Exception:
#             pass
#
#         # Step 2: 尝试 json5（容忍单引号、尾逗号等）
#         try:
#             return json5.loads(raw_content)
#         except Exception:
#             pass
#
#         # Step 3: 清洗 markdown 代码块符号
#         cleaned = re.sub(r"^```[a-zA-Z]*", "", raw_content)
#         cleaned = re.sub(r"```$", "", cleaned)
#         cleaned = cleaned.strip()
#
#         # Step 4: 正则提取第一个 {...}
#         match = re.search(r'\{[\s\S]*\}', cleaned)
#         if match:
#             json_str = match.group(0)
#
#             # 尝试标准 JSON
#             try:
#                 return json.loads(json_str)
#             except Exception:
#                 pass
#
#             # 尝试 json5
#             try:
#                 return json5.loads(json_str)
#             except Exception:
#                 pass
#
#             # 最后尝试简单修复（尾逗号、换行）
#             json_str = re.sub(r",\s*([}\]])", r"\1", json_str)
#             json_str = json_str.replace("\n", "\\n")
#             try:
#                 return json.loads(json_str)
#             except Exception:
#                 try:
#                     return json5.loads(json_str)
#                 except Exception as e:
#                     return self._save_and_raise(raw_content, e)
#
#         # 完全失败，保存原始输出
#         return self._save_and_raise(raw_content, "未匹配到 JSON 对象")
#
#     def _save_and_raise(self, raw_content: str, err):
#         path = os.path.join(os.getcwd(), "debug_raw_output.json")
#         with open(path, "w", encoding="utf-8") as f:
#             f.write(raw_content)
#         raise ValueError(f"❌ JSON解析失败: {err}, 已保存原始输出: {path}")
#
#     # =========================================================
#     #   其他工具函数
#     # =========================================================
#     def mask_phone_number(self, phone: str) -> str:
#         if len(phone) >= 11:
#             return phone[:3] + "****" + phone[7:]
#         return phone
#
#     def get_prompt(self, content: str) -> str:
#         """
#         强化提示词，确保 DeepSeek 输出只含 JSON，不带额外文字
#         """
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
#         response_format_str = json.dumps(response_format, ensure_ascii=False)
#
#         return f"""
#         你是一个文档处理助手。任务：将以下文档划分为父子结构，并标识文本中的手机号。
#
#         请严格按照 JSON 输出，不允许任何额外文本、注释或解释。
#
#         文档内容：
#         {content}
#
#         输出 JSON 格式：
#         {response_format_str}
#
#         要求：
#         - 不需要逐字逐句拆分，可以按段落或逻辑单元进行划分
#         - 每个父节点下的子节点不超过 10 个
#         - 最大层级深度限制为 3
#         - 所有属性名必须用双引号 ""
#         - 输出必须是严格可解析的 JSON
#         - 只输出 JSON
#         """


import json
import re
import os
import json5
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from rag.kdb.doc_handler import base
from openai import OpenAI


class Formatter(base.BaseDocHandler):
    def run(self, sess: base.Session):
        """
        构建符合 DTRAG 架构的层次知识结构：
        1. 调用 LLM 对文本进行语义分块；
        2. 基于 embedding 层次聚类构建树结构；
        3. 输出结构化 JSON（包含 id、parent_id、level、seq_index、content、phone）。
        """
        if not sess.text:
            print("⚠️ 无输入文本，跳过处理。")
            return

        # ===== Step 1: 调用 DeepSeek LLM 分块 =====
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )

        print("🧠 正在调用 DeepSeek 模型进行语义分块 ...")
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": self.get_prompt(sess.text)}],
            model=os.getenv("DEEPSEEK_MODEL"),
            stream=False,
            response_format={"type": "json_object"}
        )

        raw_content = chat_completion.choices[0].message.content.strip()
        rs = self._clean_json(raw_content)
        blocks = rs.get("blocks", [])
        if not blocks:
            raise ValueError("⚠️ 模型未返回有效 blocks 数据")

        print(f"✅ 分块完成，共 {len(blocks)} 个语义块。")

        # ===== Step 2: 构建层次树结构 =====
        tree_data = self._build_tree(blocks)

        # ===== Step 3: 手机号脱敏 =====
        for node in tree_data:
            for phone in node.get("phone", []):
                node["content"] = node["content"].replace(
                    phone, self.mask_phone_number(phone)
                )

        sess.text_formatted = tree_data
        print("🎯 格式化完成！")

    # =========================================================
    #   层次聚类构建树
    # =========================================================
    def _build_tree(self, blocks):
        """
        使用层次聚类算法构建 Document Tree:
        1. 使用 SentenceTransformer 计算每个文本块 embedding；
        2. 基于 cosine 相似度计算距离矩阵；
        3. 执行层次聚类；
        4. 将聚类层次映射为树结构。
        """
        # === 你的固定模型存放目录 ===
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
            print(f"⚠️ 聚类失败，使用顺序层级回退。错误: {e}")
            clustering = None

        # ===== 生成节点结构 =====
        nodes = []
        next_id = 1
        for i, blk in enumerate(blocks):
            nodes.append({
                "id": next_id,
                "level": 1,
                "parent_id": -1,
                "seq_index": i + 1,
                "content": blk.get("content", ""),
                "phone": blk.get("phones", [])
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

        for node in nodes:
            node["level"] = min(node["level"], 3)

        print(f"✅ 层次树构建完成，共 {len(nodes)} 个节点。")
        return nodes

    # =========================================================
    #   自动检测 + 下载本地模型
    # =========================================================
    def _ensure_local_bge_model(self, model_path: str):
        """
        检查本地是否存在 BGE 模型；
        如果不存在，则自动从 HuggingFace 下载并保存到该目录。
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
    #   JSON 解析增强版
    # =========================================================
    def _clean_json(self, raw_content: str) -> dict:
        """
        稳健的 JSON 解析，支持标准 JSON / JSON5 / Markdown 包裹。
        """
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

        return self._save_and_raise(raw_content, "未匹配到 JSON 对象")

    def _save_and_raise(self, raw_content: str, err):
        path = os.path.join(os.getcwd(), "debug_raw_output.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(raw_content)
        raise ValueError(f"❌ JSON解析失败: {err}, 已保存原始输出: {path}")

    # =========================================================
    #   手机号脱敏
    # =========================================================
    def mask_phone_number(self, phone: str) -> str:
        if len(phone) >= 11:
            return phone[:3] + "****" + phone[7:]
        return phone

    # =========================================================
    #   提示词：仅做语义分块
    # =========================================================
    def get_prompt(self, content: str) -> str:
        """
        模型仅负责语义分块，不再构造层级结构。
        """
        response_format = {
            "blocks": [
                {
                    "content": "逻辑完整的文本段落",
                    "phones": "数组，文本中出现的手机号"
                }
            ]
        }
        response_format_str = json.dumps(response_format, ensure_ascii=False)
        return f"""
你是一个知识文档结构分析助手。请将以下文本划分为若干语义完整的逻辑单元（即段落级知识块），
每个块应表达相对独立的主题。请检测并提取文本中出现的手机号。

请严格输出以下 JSON 结构（不包含额外说明文字）：
{response_format_str}

文档内容如下：
{content}
"""


