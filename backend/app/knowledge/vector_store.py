import os
import pickle
from typing import List, Tuple
from app.knowledge.embedder import KnowledgeEmbedder

VECTOR_STORE_DIR = "./data/vector_stores"


class VectorStoreManager:
    def __init__(self):
        self.embedder = KnowledgeEmbedder()
        self._stores = {}
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    def _get_store_path(self, collection_name: str) -> str:
        return os.path.join(VECTOR_STORE_DIR, f"{collection_name}.pkl")

    def get_store(self, collection_name: str):
        if collection_name not in self._stores:
            from langchain_community.vectorstores import FAISS
            store_path = self._get_store_path(collection_name)
            if os.path.exists(store_path):
                try:
                    with open(store_path, "rb") as f:
                        self._stores[collection_name] = pickle.load(f)
                except Exception:
                    self._stores[collection_name] = None
            else:
                self._stores[collection_name] = None
        return self._stores[collection_name]

    def _save_store(self, collection_name: str, store):
        store_path = self._get_store_path(collection_name)
        os.makedirs(os.path.dirname(store_path), exist_ok=True)
        with open(store_path, "wb") as f:
            pickle.dump(store, f)

    async def add_texts(self, collection_name: str, texts: List[str], metadatas: List[dict]):
        from langchain_community.vectorstores import FAISS
        store = self.get_store(collection_name)
        if texts:
            if store is None:
                store = FAISS.from_texts(
                    texts=texts,
                    embedding=self.embedder.embed_texts,
                    metadatas=metadatas,
                )
            else:
                store.add_texts(texts=texts, metadatas=metadatas)
            self._stores[collection_name] = store
            self._save_store(collection_name, store)

    async def similarity_search(
        self, collection_name: str, query: str, k: int = 5
    ) -> List[Tuple]:
        store = self.get_store(collection_name)
        if store:
            docs = store.similarity_search_with_score(query, k=k)
            return [(doc.page_content, doc.metadata, score) for doc, score in docs]
        return []

    def create_index(self, collection_name: str):
        """确保索引目录存在"""
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
