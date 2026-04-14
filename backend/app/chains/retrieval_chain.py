from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from app.knowledge.vector_store import VectorStoreManager
from app.knowledge.embedder import KnowledgeEmbedder

class RetrievalChain:
    def __init__(self):
        self.vector_store = VectorStoreManager()
        self.embedder = KnowledgeEmbedder()

    def create_cause_chain(self, llm):
        """案由检索链"""
        template = """基于以下案由知识库信息，回答问题。

知识库信息：
{context}

问题：{question}

请从知识库中找出最相关的案由信息。"""

        prompt = ChatPromptTemplate.from_template(template)

        def format_docs(docs):
            return "\n".join([getattr(doc, 'page_content', str(doc)) for doc in docs])

        chain = (
            RunnablePassthrough.assign(context=lambda x: format_docs(x.get("docs", []))),
            prompt,
            llm,
            StrOutputParser()
        )
        return chain

    def create_evidence_chain(self, llm):
        """证据知识检索链"""
        template = """基于以下证据知识库信息，提供证据收集指导。

知识库信息：
{context}

用户情况：{situation}

请提供针对性的证据收集建议。"""
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | llm | StrOutputParser()

    def create_risk_chain(self, llm):
        """风险知识检索链"""
        template = """基于以下风险知识库，分析案件风险。

知识库信息：
{context}

案件信息：
{case_info}

请识别主要风险点并提供规避建议。"""
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | llm | StrOutputParser()
