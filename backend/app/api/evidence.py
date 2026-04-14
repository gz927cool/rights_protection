from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.database import get_db
from app.db.repositories import EvidenceRepository
from app.models.schemas import EvidenceResponse
from app.utils.file_storage import save_file
from fastapi import UploadFile, File

router = APIRouter(prefix="/api", tags=["evidence"])

@router.post("/cases/{case_id}/evidence", response_model=EvidenceResponse)
async def upload_evidence(
    case_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # 保存文件
    file_url = await save_file(file, str(case_id))

    # 创建证据记录
    repo = EvidenceRepository(db)
    evidence = await repo.create(
        case_id=case_id,
        name=file.filename,
        file_url=file_url,
        type="A"  # 默认已有
    )
    return evidence

@router.get("/cases/{case_id}/evidence", response_model=list[EvidenceResponse])
async def get_evidence(case_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = EvidenceRepository(db)
    evidence_list = await repo.get_by_case_id(case_id)
    return evidence_list

@router.delete("/evidence/{evidence_id}")
async def delete_evidence(evidence_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = EvidenceRepository(db)
    await repo.delete(evidence_id)
    return {"status": "ok"}
