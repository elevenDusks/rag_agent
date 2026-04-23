from langchain_core.documents import Document

from ..models.model_registry import crossEncoder_model

class Rerank:
    def __init__(self):
        pass
    async def rerank_documents(self, question:str, docs:list[Document], k:int):
        # 构造输入对
        pairs = [[question, doc.page_content] for doc in docs]
        scores = crossEncoder_model.predict(pairs)

        # 按分数排序
        ranked_docs = [doc for _, doc in sorted(zip(scores, docs), reverse=True)]

        return ranked_docs[:k]

