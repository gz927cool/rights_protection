from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class CaseStatus(str, Enum):
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    SUBMITTED = "已提交"


class EvidenceType(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class RiskLevel(str, Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


# Auth
class LoginRequest(BaseModel):
    phone: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Case
class CaseCreate(BaseModel):
    pass


class CaseResponse(BaseModel):
    id: UUID
    user_id: UUID
    status: CaseStatus
    current_step: int
    cause_codes: List[str]
    case_description: Optional[str]
    created_at: datetime
    updated_at: datetime


class CaseAnswerRequest(BaseModel):
    question_id: str
    answer_value: Any


class CaseAnswerResponse(BaseModel):
    id: UUID
    case_id: UUID
    question_id: str
    answer_value: Any
    answered_at: datetime


# Cause
class CauseResponse(BaseModel):
    id: UUID
    name: str
    code: str
    level: int
    children: List["CauseResponse"] = []


# Evidence
class EvidenceCreate(BaseModel):
    type: EvidenceType
    name: str
    file_url: Optional[str] = None
    note: Optional[str] = None


class EvidenceResponse(BaseModel):
    id: UUID
    case_id: UUID
    type: EvidenceType
    name: str
    file_url: Optional[str]
    status: Optional[str]
    ai_evaluation: Optional[dict]
    note: Optional[str]
    created_at: datetime


# Document
class DocumentResponse(BaseModel):
    id: UUID
    case_id: UUID
    type: str
    content: Optional[str]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class DocumentGenerateRequest(BaseModel):
    document_type: str = "仲裁申请书"


# AI
class CaseAnalysisRequest(BaseModel):
    case_id: UUID


class CaseAnalysisResponse(BaseModel):
    case_description: str
    cause_codes: List[str]


class EvidenceEvalRequest(BaseModel):
    evidence_id: UUID


class RiskAssessmentRequest(BaseModel):
    case_id: UUID


class RiskAssessmentResponse(BaseModel):
    risk_points: List[dict]
    overall_level: RiskLevel
    suggestions: List[str]


class DocumentGenRequest(BaseModel):
    case_id: UUID
    document_type: str = "仲裁申请书"


class DocumentGenResponse(BaseModel):
    document_id: UUID
    content: str


class ContextualAnalysisRequest(BaseModel):
    case_id: UUID
    current_step: int = Field(..., ge=1, le=9)
    context_data: dict = Field(
        ...,
        description="包含 case_summary、answers_this_step、previous_steps_summary、evidence_status、user_question"
    )
