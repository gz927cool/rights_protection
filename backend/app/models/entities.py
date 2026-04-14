from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy import Uuid
from datetime import datetime
import uuid
import enum


class CaseStatus(str, enum.Enum):
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    SUBMITTED = "已提交"


class EvidenceType(str, enum.Enum):
    A = "A"  # 已有
    B = "B"  # 可补充
    C = "C"  # 无法取得


class RiskLevel(str, enum.Enum):
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), unique=True, nullable=False)
    name = Column(String(100))
    union_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    cases = relationship("Case", back_populates="user")


class Case(Base):
    __tablename__ = "cases"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"))
    status = Column(Enum(CaseStatus), default=CaseStatus.IN_PROGRESS)
    current_step = Column(Integer, default=1)
    cause_codes = Column(JSON, default=list)
    case_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="cases")
    answers = relationship("CaseAnswer", back_populates="case")
    evidence = relationship("Evidence", back_populates="case")
    documents = relationship("Document", back_populates="case")
    risk_assessment = relationship("RiskAssessment", back_populates="case", uselist=False)


class CaseAnswer(Base):
    __tablename__ = "case_answers"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id = Column(Uuid, ForeignKey("cases.id"))
    question_id = Column(String(50))
    answer_value = Column(JSON)
    answered_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("Case", back_populates="answers")


class CauseOfAction(Base):
    __tablename__ = "causes_of_action"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    code = Column(String(20), unique=True)
    parent_id = Column(Uuid, ForeignKey("causes_of_action.id"))
    level = Column(Integer)  # 1, 2, 3
    common_questions = Column(JSON, default=list)
    special_questions = Column(JSON, default=list)
    children = relationship("CauseOfAction")


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id = Column(Uuid, ForeignKey("cases.id"))
    type = Column(Enum(EvidenceType))
    name = Column(String(200))
    file_url = Column(String(500))
    status = Column(String(50))
    ai_evaluation = Column(JSON)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("Case", back_populates="evidence")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id = Column(Uuid, ForeignKey("cases.id"))
    type = Column(String(50))  # 仲裁申请书, 调解申请书
    content = Column(Text)
    status = Column(String(20), default="草稿")
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    case = relationship("Case", back_populates="documents")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id = Column(Uuid, ForeignKey("cases.id"), unique=True)
    risk_points = Column(JSON, default=list)
    overall_level = Column(Enum(RiskLevel))
    suggestions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("Case", back_populates="risk_assessment")
