from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
from app.db.repositories import CaseRepository, DocumentRepository
from app.agents.document_gen_agent import DocumentGenAgent
from app.models.entities import Document
from typing import List, Optional

class DocumentService:
    def __init__(self):
        self.agent = DocumentGenAgent()

    async def generate(
        self,
        case_id: UUID,
        document_type: str,
        case_description: str,
        claims: List[str],
        db: AsyncSession
    ) -> Document:
        # 调用 AI Agent 生成文书
        result = await self.agent.run({
            "case_description": case_description,
            "claims": claims,
            "document_type": document_type
        })

        # 保存文书
        doc_repo = DocumentRepository(db)
        document = await doc_repo.create(
            case_id=case_id,
            type=document_type,
            content=result.get("content", "")
        )

        return document

    async def get_by_case(self, case_id: UUID, db: AsyncSession) -> List[Document]:
        doc_repo = DocumentRepository(db)
        return await doc_repo.get_by_case_id(case_id)

    async def update_content(
        self,
        doc_id: UUID,
        content: str,
        db: AsyncSession
    ) -> Document:
        doc_repo = DocumentRepository(db)
        return await doc_repo.update_content(doc_id, content)
