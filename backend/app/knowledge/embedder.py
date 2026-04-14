from typing import List
from app.config import settings

class KnowledgeEmbedder:
    def __init__(self):
        self.embeddings = None
        embedding_model = getattr(settings, 'EMBEDDING_MODEL', 'text-embedding-v4')
        # 使用 OpenAI-compatible Embedding API (DashScope)
        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import OpenAIEmbeddings
                self.embeddings = OpenAIEmbeddings(
                    model=embedding_model,
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL
                )
            except ImportError:
                self.embeddings = None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if self.embeddings:
            return self.embeddings.embed_documents(texts)
        # Fallback: 返回零向量
        return [[0.0] * 1536 for _ in texts]

    def embed_query(self, query: str) -> List[float]:
        if self.embeddings:
            return self.embeddings.embed_query(query)
        return [0.0] * 1536
