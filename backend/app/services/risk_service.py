from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.repositories import CaseRepository, EvidenceRepository, RiskAssessmentRepository
from app.agents.risk_assess_agent import RiskAssessAgent
from app.models.entities import RiskLevel

class RiskService:
    def __init__(self):
        self.agent = RiskAssessAgent()

    async def assess(self, case_id: UUID, db: AsyncSession) -> dict:
        # 获取案件信息
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(case_id)
        if not case:
            raise ValueError("Case not found")

        # 获取证据状态
        evidence_repo = EvidenceRepository(db)
        evidence_list = await evidence_repo.get_by_case(case_id)
        evidence_status = {
            "total": len(evidence_list),
            "type_a": len([e for e in evidence_list if e.type and e.type.value == "A"]),
            "type_b": len([e for e in evidence_list if e.type and e.type.value == "B"]),
            "type_c": len([e for e in evidence_list if e.type and e.type.value == "C"])
        }

        # 调用 AI Agent 评估
        result = await self.agent.run({
            "case_description": case.case_description or "",
            "cause_codes": case.cause_codes or [],
            "evidence_status": evidence_status
        })

        # 保存评估结果
        risk_repo = RiskAssessmentRepository(db)
        assessment = await risk_repo.create(
            case_id=case_id,
            risk_points=result.get("risk_points", []),
            overall_level=RiskLevel(result.get("overall_level", "中")),
            suggestions=result.get("suggestions", [])
        )

        return {
            "id": str(assessment.id),
            "case_id": str(case_id),
            "risk_points": assessment.risk_points,
            "overall_level": assessment.overall_level.value if hasattr(assessment.overall_level, 'value') else assessment.overall_level,
            "suggestions": assessment.suggestions,
            "created_at": assessment.created_at.isoformat() if assessment.created_at else None
        }
