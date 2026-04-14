from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List
from app.db.database import get_db
from app.db.repositories import CauseOfActionRepository
from app.models.schemas import CauseResponse

router = APIRouter(prefix="/api/causes", tags=["causes"])


@router.get("", response_model=List[CauseResponse])
async def list_causes(db: AsyncSession = Depends(get_db)):
    """获取所有案由（树形结构）"""
    repo = CauseOfActionRepository(db)
    causes = await repo.get_root_causes()
    return causes


@router.get("/{cause_id}", response_model=CauseResponse)
async def get_cause(cause_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取案由详情"""
    repo = CauseOfActionRepository(db)
    cause = await repo.get_by_id(cause_id)
    if not cause:
        raise HTTPException(404, "Cause not found")
    return cause


@router.get("/{cause_id}/questions")
async def get_cause_questions(cause_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取案由对应的问题列表"""
    repo = CauseOfActionRepository(db)
    cause = await repo.get_by_id(cause_id)
    if not cause:
        raise HTTPException(404, "Cause not found")

    # 返回通用问题和小类问题
    return {
        "common_questions": cause.common_questions or [],
        "special_questions": cause.special_questions or []
    }
