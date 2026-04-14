from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime
from typing import List, Optional

from app.models.entities import (
    User, Case, CaseAnswer, Evidence, Document,
    RiskAssessment, CauseOfAction, CaseStatus
)


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def create(self, phone: str, name: str = None, union_id: str = None) -> User:
        user = User(phone=phone, name=name, union_id=union_id)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user


class CaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID, cause_codes: list = None, case_description: str = None) -> Case:
        case = Case(
            user_id=user_id,
            cause_codes=cause_codes or [],
            case_description=case_description
        )
        self.db.add(case)
        await self.db.commit()
        await self.db.refresh(case)
        return case

    async def get_by_id(self, case_id: UUID) -> Optional[Case]:
        result = await self.db.execute(
            select(Case)
            .options(
                selectinload(Case.answers),
                selectinload(Case.evidence),
                selectinload(Case.documents),
                selectinload(Case.risk_assessment)
            )
            .where(Case.id == case_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> List[Case]:
        result = await self.db.execute(select(Case).where(Case.user_id == user_id))
        return list(result.scalars().all())

    async def update_step(self, case_id: UUID, step: int) -> None:
        await self.db.execute(
            update(Case)
            .where(Case.id == case_id)
            .values(current_step=step, updated_at=datetime.utcnow())
        )
        await self.db.commit()

    async def update_status(self, case_id: UUID, status: CaseStatus) -> None:
        await self.db.execute(
            update(Case)
            .where(Case.id == case_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await self.db.commit()

    async def update_description(self, case_id: UUID, description: str) -> None:
        await self.db.execute(
            update(Case)
            .where(Case.id == case_id)
            .values(case_description=description, updated_at=datetime.utcnow())
        )
        await self.db.commit()

    async def update_cause_codes(self, case_id: UUID, cause_codes: list) -> None:
        await self.db.execute(
            update(Case)
            .where(Case.id == case_id)
            .values(cause_codes=cause_codes, updated_at=datetime.utcnow())
        )
        await self.db.commit()


class CaseAnswerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, case_id: UUID, question_id: str, answer_value: any) -> CaseAnswer:
        answer = CaseAnswer(
            case_id=case_id,
            question_id=question_id,
            answer_value=answer_value
        )
        self.db.add(answer)
        await self.db.commit()
        await self.db.refresh(answer)
        return answer

    async def get_by_case_id(self, case_id: UUID) -> List[CaseAnswer]:
        result = await self.db.execute(
            select(CaseAnswer).where(CaseAnswer.case_id == case_id)
        )
        return list(result.scalars().all())

    async def get_by_question(self, case_id: UUID, question_id: str) -> Optional[CaseAnswer]:
        result = await self.db.execute(
            select(CaseAnswer)
            .where(CaseAnswer.case_id == case_id)
            .where(CaseAnswer.question_id == question_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, case_id: UUID, question_id: str, answer_value: any) -> CaseAnswer:
        existing = await self.get_by_question(case_id, question_id)
        if existing:
            existing.answer_value = answer_value
            existing.answered_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        return await self.create(case_id, question_id, answer_value)


class EvidenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, case_id: UUID, type: str, name: str, file_url: str = None, note: str = None) -> Evidence:
        evidence = Evidence(
            case_id=case_id,
            type=type,
            name=name,
            file_url=file_url,
            note=note
        )
        self.db.add(evidence)
        await self.db.commit()
        await self.db.refresh(evidence)
        return evidence

    async def get_by_id(self, evidence_id: UUID) -> Optional[Evidence]:
        result = await self.db.execute(select(Evidence).where(Evidence.id == evidence_id))
        return result.scalar_one_or_none()

    async def get_by_case_id(self, case_id: UUID) -> List[Evidence]:
        result = await self.db.execute(select(Evidence).where(Evidence.case_id == case_id))
        return list(result.scalars().all())

    async def update_ai_evaluation(self, evidence_id: UUID, ai_evaluation: dict) -> None:
        await self.db.execute(
            update(Evidence)
            .where(Evidence.id == evidence_id)
            .values(ai_evaluation=ai_evaluation)
        )
        await self.db.commit()

    async def update_status(self, evidence_id: UUID, status: str) -> None:
        await self.db.execute(
            update(Evidence)
            .where(Evidence.id == evidence_id)
            .values(status=status)
        )
        await self.db.commit()

    async def delete(self, evidence_id: UUID) -> None:
        await self.db.execute(delete(Evidence).where(Evidence.id == evidence_id))
        await self.db.commit()


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, case_id: UUID, type: str, content: str = None) -> Document:
        document = Document(
            case_id=case_id,
            type=type,
            content=content
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def get_by_id(self, document_id: UUID) -> Optional[Document]:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def get_by_case_id(self, case_id: UUID) -> List[Document]:
        result = await self.db.execute(select(Document).where(Document.case_id == case_id))
        return list(result.scalars().all())

    async def get_by_case_and_type(self, case_id: UUID, type: str) -> Optional[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.case_id == case_id)
            .where(Document.type == type)
        )
        return result.scalar_one_or_none()

    async def update_content(self, document_id: UUID, content: str) -> None:
        await self.db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(content=content, version=Document.version + 1, updated_at=datetime.utcnow())
        )
        await self.db.commit()

    async def update_status(self, document_id: UUID, status: str) -> None:
        await self.db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        await self.db.commit()


class RiskAssessmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, case_id: UUID, risk_points: list, overall_level: str, suggestions: list) -> RiskAssessment:
        assessment = RiskAssessment(
            case_id=case_id,
            risk_points=risk_points,
            overall_level=overall_level,
            suggestions=suggestions
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment

    async def get_by_case_id(self, case_id: UUID) -> Optional[RiskAssessment]:
        result = await self.db.execute(
            select(RiskAssessment).where(RiskAssessment.case_id == case_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, case_id: UUID, risk_points: list, overall_level: str, suggestions: list) -> RiskAssessment:
        existing = await self.get_by_case_id(case_id)
        if existing:
            existing.risk_points = risk_points
            existing.overall_level = overall_level
            existing.suggestions = suggestions
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        return await self.create(case_id, risk_points, overall_level, suggestions)


class CauseOfActionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, cause_id: UUID) -> Optional[CauseOfAction]:
        result = await self.db.execute(select(CauseOfAction).where(CauseOfAction.id == cause_id))
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[CauseOfAction]:
        result = await self.db.execute(select(CauseOfAction).where(CauseOfAction.code == code))
        return result.scalar_one_or_none()

    async def get_by_level(self, level: int) -> List[CauseOfAction]:
        result = await self.db.execute(
            select(CauseOfAction)
            .options(selectinload(CauseOfAction.children))
            .where(CauseOfAction.level == level)
        )
        return list(result.scalars().all())

    async def get_root_causes(self) -> List[CauseOfAction]:
        result = await self.db.execute(
            select(CauseOfAction)
            .options(selectinload(CauseOfAction.children))
            .where(CauseOfAction.parent_id == None)
        )
        return list(result.scalars().all())

    async def create(self, name: str, code: str, level: int, parent_id: UUID = None,
                     common_questions: list = None, special_questions: list = None) -> CauseOfAction:
        cause = CauseOfAction(
            name=name,
            code=code,
            level=level,
            parent_id=parent_id,
            common_questions=common_questions or [],
            special_questions=special_questions or []
        )
        self.db.add(cause)
        await self.db.commit()
        await self.db.refresh(cause)
        return cause
