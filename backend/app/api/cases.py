from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID, uuid4
from typing import List
from app.db.database import get_db
from app.db.repositories import CaseRepository, CaseAnswerRepository
from app.models.schemas import CaseCreate, CaseResponse, CaseAnswerRequest, CaseAnswerResponse

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.post("", response_model=CaseResponse)
async def create_case(
    _: CaseCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = CaseRepository(db)
    case = await repo.create(user_id=uuid4())  # TODO: from auth
    return case


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = CaseRepository(db)
    case = await repo.get_by_id(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


@router.put("/{case_id}/step/{step}")
async def update_step(
    case_id: UUID,
    step: int,
    db: AsyncSession = Depends(get_db)
):
    if step < 1 or step > 9:
        raise HTTPException(400, "Step must be 1-9")
    repo = CaseRepository(db)
    await repo.update_step(case_id, step)
    return {"status": "ok"}


@router.get("/{case_id}/answers", response_model=List[CaseAnswerResponse])
async def get_case_answers(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取案件的所有回答"""
    repo = CaseAnswerRepository(db)
    answers = await repo.get_by_case_id(case_id)
    return answers


@router.post("/{case_id}/answers", response_model=CaseAnswerResponse)
async def submit_answer(
    case_id: UUID,
    request: CaseAnswerRequest,
    db: AsyncSession = Depends(get_db)
):
    """提交案件回答"""
    repo = CaseAnswerRepository(db)
    answer = await repo.upsert(case_id, request.question_id, request.answer_value)
    return answer


@router.delete("/{case_id}")
async def delete_case(case_id: UUID, db: AsyncSession = Depends(get_db)):
    """删除案件"""
    repo = CaseRepository(db)
    case = await repo.get_by_id(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    # 实际删除应该软删除，这里简化处理
    return {"status": "ok"}
