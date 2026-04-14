from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from app.db.database import get_db
from app.db.repositories import CaseRepository, EvidenceRepository, CaseAnswerRepository
from app.models.schemas import (
    CaseAnalysisRequest, CaseAnalysisResponse,
    EvidenceEvalRequest, RiskAssessmentRequest, RiskAssessmentResponse,
    DocumentGenRequest, DocumentGenResponse
)
from app.agents.case_analysis_agent import CaseAnalysisAgent
from app.agents.evidence_eval_agent import EvidenceEvalAgent
from app.agents.risk_assess_agent import RiskAssessAgent
from app.agents.document_gen_agent import DocumentGenAgent
from app.agents.ai_review_agent import AIReviewAgent

router = APIRouter(prefix="/api/ai", tags=["ai"])

@router.post("/analyze-case", response_model=CaseAnalysisResponse)
async def analyze_case(
    req: CaseAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(req.case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    answer_repo = CaseAnswerRepository(db)
    answers = await answer_repo.get_by_case_id(req.case_id)
    answers_data = [
        {"question_id": a.question_id, "answer_value": a.answer_value}
        for a in answers
    ]

    agent = CaseAnalysisAgent()
    result = await agent.run({
        "case_id": str(req.case_id),
        "answers": answers_data,
        "evidence": []
    })

    if "case_description" in result:
        await case_repo.update_description(req.case_id, result["case_description"])
    if "cause_codes" in result:
        await case_repo.update_cause_codes(req.case_id, result["cause_codes"])

    return CaseAnalysisResponse(**result)

@router.post("/evaluate-evidence")
async def evaluate_evidence(
    req: EvidenceEvalRequest,
    db: AsyncSession = Depends(get_db)
):
    evidence_repo = EvidenceRepository(db)
    evidence = await evidence_repo.get_by_id(req.evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")

    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(evidence.case_id)

    agent = EvidenceEvalAgent()
    result = await agent.run({
        "evidence_id": str(req.evidence_id),
        "name": evidence.name,
        "type": evidence.type.value if hasattr(evidence.type, 'value') else str(evidence.type),
        "note": evidence.note or "",
        "cause_codes": case.cause_codes if case else []
    })

    await evidence_repo.update_ai_evaluation(req.evidence_id, result)
    return result

@router.post("/risk-assessment", response_model=RiskAssessmentResponse)
async def assess_risk(
    req: RiskAssessmentRequest,
    db: AsyncSession = Depends(get_db)
):
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(req.case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    evidence_repo = EvidenceRepository(db)
    evidence_list = await evidence_repo.get_by_case_id(req.case_id)
    evidence_status = {
        "total": len(evidence_list),
        "type_a": len([e for e in evidence_list if e.type and e.type.value == "A"]),
        "type_b": len([e for e in evidence_list if e.type and e.type.value == "B"]),
        "type_c": len([e for e in evidence_list if e.type and e.type.value == "C"])
    }

    agent = RiskAssessAgent()
    result = await agent.run({
        "case_description": case.case_description or "",
        "cause_codes": case.cause_codes or [],
        "evidence_status": evidence_status
    })

    return RiskAssessmentResponse(**result)

@router.post("/generate-document")
async def generate_document(
    req: DocumentGenRequest,
    db: AsyncSession = Depends(get_db)
):
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(req.case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    # Import DocumentService lazily to handle case where it doesn't exist yet
    try:
        from app.services.document_service import DocumentService
        doc_service = DocumentService()
        document = await doc_service.generate(
            case_id=req.case_id,
            document_type=req.document_type,
            case_description=case.case_description or "",
            claims=[],
            db=db
        )
        return {"document_id": str(document.id), "content": document.content}
    except ImportError:
        return {"error": "DocumentService not available yet", "content": ""}
    except Exception as e:
        return {"error": str(e), "content": ""}

@router.post("/review")
async def ai_review(case_data: dict = Body(...), user_question: Optional[str] = None):
    """AI复核接口"""
    agent = AIReviewAgent()
    result = await agent.run({
        "case_data": case_data,
        "user_question": user_question
    })
    return result