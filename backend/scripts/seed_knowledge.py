"""FAISS 知识库初始化脚本"""
import asyncio
from pathlib import Path
from app.knowledge.loader import KnowledgeLoader
from app.knowledge.vector_store import VectorStoreManager
from app.knowledge.embedder import KnowledgeEmbedder
from app.config import settings

async def seed_knowledge():
    loader = KnowledgeLoader()
    embedder = KnowledgeEmbedder()

    # 案由知识库
    causes = loader.load_causes()
    cause_texts = []
    cause_metas = []
    for cause in causes:
        text = f"案由: {cause['name']}\n编码: {cause['code']}\n问题: {cause.get('questions', [])}"
        cause_texts.append(text)
        cause_metas.append({"source": cause['code']})

    # 证据知识库
    evidence = loader.load_evidence_knowledge()
    evidence_texts = []
    evidence_metas = []
    for ev in evidence:
        text = f"证据类型: {ev['name']}\n用途: {ev['purpose']}\n收集方法: {ev.get('how_to_collect', '')}"
        evidence_texts.append(text)
        evidence_metas.append({"source": ev['name']})

    # 风险知识库
    risks = loader.load_risk_knowledge()
    risk_texts = []
    risk_metas = []
    for risk in risks:
        text = f"风险类型: {risk['type']}\n描述: {risk['description']}\n规避建议: {risk.get('suggestions', [])}"
        risk_texts.append(text)
        risk_metas.append({"source": risk['type']})

    vector_store = VectorStoreManager()

    # 插入数据到 FAISS 向量存储
    try:
        await vector_store.add_texts("causes", cause_texts, cause_metas)
        await vector_store.add_texts("evidence", evidence_texts, evidence_metas)
        await vector_store.add_texts("risks", risk_texts, risk_metas)
        print("Knowledge base seeded successfully!")
    except Exception as e:
        print(f"Warning: Could not seed vector store: {e}")
        print("Knowledge files are ready for manual seeding when FAISS is available.")

if __name__ == "__main__":
    asyncio.run(seed_knowledge())
