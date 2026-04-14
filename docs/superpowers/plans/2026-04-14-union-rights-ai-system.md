# 工会劳动维权 AI 引导系统 - 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一套 AI 增强的劳动维权自助服务系统，包含 9 步引导流程 + RAG 知识库 + AI Agent

**Architecture:** 前后端分离架构。前端 React Web 应用驱动状态机管理 9 步流程；后端 FastAPI 提供 REST API，LangChain ≥1.0 编排 AI Agent；PostgreSQL 存储业务数据，Milvus 向量数据库支持 RAG 检索。

**Tech Stack:** React 18+ / TypeScript / Zustand / React Query | FastAPI / Python 3.10+ / LangChain ≥1.0 | PostgreSQL 15+ / Milvus | Docker Compose

---

## 系统架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    React Web App (:3000)                  │
└─────────────────────────────────────────────────────────┘
                            │ HTTP
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend (:8000)                │
│  ┌─────────────────────────────────────────────────────┐│
│  │ API Layer: /api/auth, /api/cases, /api/ai, ...    ││
│  │ Services: CaseService, CauseService, DocumentService││
│  │ Agents: CaseAnalysis, EvidenceEval, RiskAssess, ... ││
│  │ Chains: RetrievalChain (RAG)                        ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                │                    │
                ▼                    ▼
        ┌───────────────┐    ┌───────────────┐
        │  PostgreSQL   │    │    Milvus     │
        │   (:5432)     │    │   (:19530)    │
        └───────────────┘    └───────────────┘
```

---

## 文件结构

```
/root
├── frontend/                          # React Web 应用
│   ├── src/
│   │   ├── components/               # UI 组件
│   │   │   ├── layout/              # AppShell, StepWizard, StepContent
│   │   │   ├── business/            # CauseSelector, QuestionCard, AmountCalculator...
│   │   │   └── ai/                  # AIChatPanel, AIFeedbackCard
│   │   ├── pages/                   # Home, CaseWizard, CaseDetail
│   │   ├── stores/                  # caseStore, userStore (Zustand)
│   │   ├── hooks/                   # useCase, useAI, useStep
│   │   ├── services/                # api.ts, aiService.ts
│   │   └── utils/                   # 工具函数
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                          # FastAPI 应用
│   ├── app/
│   │   ├── main.py                  # FastAPI 入口
│   │   ├── config.py                # 配置管理
│   │   ├── api/                    # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # 认证 API
│   │   │   ├── cases.py            # 案件 API
│   │   │   ├── causes.py           # 案由 API
│   │   │   ├── documents.py        # 文书 API
│   │   │   ├── evidence.py         # 证据 API
│   │   │   └── ai.py               # AI 服务 API
│   │   ├── services/               # 业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── case_service.py
│   │   │   ├── cause_service.py
│   │   │   ├── document_service.py
│   │   │   └── evidence_service.py
│   │   ├── agents/                 # AI Agents (LangChain ≥1.0)
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py       # Agent 基类
│   │   │   ├── case_analysis_agent.py    # Step 4: 案情分析 (ReAct)
│   │   │   ├── evidence_eval_agent.py    # Step 5: 证据审核 (Chain)
│   │   │   ├── risk_assess_agent.py      # Step 6: 风险评估 (ReAct)
│   │   │   ├── document_gen_agent.py     # Step 7: 文书生成 (ReAct)
│   │   │   └── ai_review_agent.py        # Step 9: AI 复核 (Chain)
│   │   ├── chains/                 # LangChain Chains
│   │   │   ├── __init__.py
│   │   │   └── retrieval_chain.py  # RAG 检索链
│   │   ├── knowledge/              # 知识库处理
│   │   │   ├── __init__.py
│   │   │   ├── loader.py          # 知识文件加载
│   │   │   ├── embedder.py        # 向量化处理
│   │   │   └── vector_store.py     # Milvus 操作
│   │   ├── models/                 # Pydantic 模型
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py         # Request/Response schemas
│   │   │   └── entities.py         # 数据库实体
│   │   ├── db/                     # 数据库操作
│   │   │   ├── __init__.py
│   │   │   ├── database.py         # 数据库连接
│   │   │   └── repositories.py     # CRUD 操作
│   │   └── utils/                  # 工具函数
│   │       ├── security.py         # JWT 工具
│   │       └── file_storage.py     # 文件存储
│   ├── data/                       # 知识库数据
│   │   ├── causes/                 # 案由数据 YAML
│   │   ├── templates/              # 文书模板
│   │   ├── evidence/               # 证据知识
│   │   └── risks/                  # 风险知识
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml
└── SPEC.md
```

---

## 实施阶段划分

| 阶段 | 范围 | 目标 |
|------|------|------|
| Phase 1 | 基础框架 | 项目脚手架、数据库、基础 API |
| Phase 2 | 知识库 + AI | RAG 检索、5 个 AI Agent |
| Phase 3 | 业务功能 | 9 步流程、证据管理、文书生成 |
| Phase 4 | 完善 + 部署 | 风险评估、Docker 部署 |

---

## Phase 1: 基础框架

### Task 1: 项目脚手架搭建

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/index.html`
- Create: `backend/requirements.txt`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `docker-compose.yml`

- [ ] **Step 1: 创建前端项目结构**

```bash
mkdir -p frontend/src/{components/{layout,business,ai},pages,stores,hooks,services,utils}
touch frontend/src/main.tsx frontend/src/App.tsx
```

- [ ] **Step 2: 创建前端 package.json**

```json
{
  "name": "union-rights-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "zustand": "^4.4.0",
    "@tanstack/react-query": "^5.8.0",
    "axios": "^1.6.0",
    "dayjs": "^1.11.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

- [ ] **Step 3: 创建前端 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 4: 创建后端 requirements.txt**

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0
sqlalchemy==2.0.25
asyncpg==0.29.0
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
aiofiles==23.2.1
langchain>=1.0.0
langchain-core>=1.0.0
langchain-milvus>=1.0.0
pymilvus>=2.3.0
openai>=1.3.0
pyyaml==6.0.1
```

- [ ] **Step 5: 创建 docker-compose.yml**

```yaml
version: '3.8'
services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/union_db
      - MILVUS_URL=milvus:19530
      - QWEN_API_KEY=${QWEN_API_KEY}
    depends_on:
      - postgres
      - milvus

  postgres:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=union_db

  milvus:
    image: milvusdb/milvus:v2.3.0
    ports:
      - "19530:19530"
    volumes:
      - milvusdata:/var/lib/milvus

volumes:
  pgdata:
  milvusdata:
```

- [ ] **Step 6: 提交 Phase 1 脚手架**

```bash
git add -A
git commit -m "phase 1: project scaffolding"
```

---

### Task 2: 数据库模型实现

**Files:**
- Create: `backend/app/models/entities.py`
- Create: `backend/app/models/schemas.py`
- Create: `backend/app/db/database.py`
- Create: `backend/app/db/repositories.py`
- Create: `backend/app/api/cases.py`

- [ ] **Step 1: 创建数据库实体 models/entities.py**

```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
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
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), unique=True, nullable=False)
    name = Column(String(100))
    union_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    cases = relationship("Case", back_populates="user")

class Case(Base):
    __tablename__ = "cases"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
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
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
    question_id = Column(String(50))
    answer_value = Column(JSON)
    answered_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("Case", back_populates="answers")

class CauseOfAction(Base):
    __tablename__ = "causes_of_action"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    code = Column(String(20), unique=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("causes_of_action.id"))
    level = Column(Integer)  # 1, 2, 3
    common_questions = Column(JSON, default=list)
    special_questions = Column(JSON, default=list)
    children = relationship("CauseOfAction")

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
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
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
    type = Column(String(50))  # 仲裁申请书, 调解申请书
    content = Column(Text)
    status = Column(String(20), default="草稿")
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    case = relationship("Case", back_populates="documents")

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), unique=True)
    risk_points = Column(JSON, default=list)
    overall_level = Column(Enum(RiskLevel))
    suggestions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("Case", back_populates="risk_assessment")
```

- [ ] **Step 2: 创建 Pydantic Schemas models/schemas.py**

```python
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
    code: str  # 验证码

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
```

- [ ] **Step 3: 创建数据库连接 db/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 4: 创建 Repository db/repositories.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.models.entities import Case, CaseAnswer, Evidence, Document, RiskAssessment, User
from typing import List, Optional
from uuid import UUID

class CaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID) -> Case:
        case = Case(user_id=user_id)
        self.db.add(case)
        await self.db.commit()
        await self.db.refresh(case)
        return case

    async def get_by_id(self, case_id: UUID) -> Optional[Case]:
        result = await self.db.execute(select(Case).where(Case.id == case_id))
        return result.scalar_one_or_none()

    async def update_step(self, case_id: UUID, step: int) -> None:
        await self.db.execute(
            update(Case).where(Case.id == case_id).values(current_step=step)
        )
        await self.db.commit()

    async def update_description(self, case_id: UUID, description: str) -> None:
        await self.db.execute(
            update(Case).where(Case.id == case_id).values(case_description=description)
        )
        await self.db.commit()

    async def update_causes(self, case_id: UUID, cause_codes: List[str]) -> None:
        await self.db.execute(
            update(Case).where(Case.id == case_id).values(cause_codes=cause_codes)
        )
        await self.db.commit()

class CaseAnswerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, case_id: UUID, question_id: str, answer_value: any) -> CaseAnswer:
        answer = CaseAnswer(case_id=case_id, question_id=question_id, answer_value=answer_value)
        self.db.add(answer)
        await self.db.commit()
        await self.db.refresh(answer)
        return answer

    async def get_by_case(self, case_id: UUID) -> List[CaseAnswer]:
        result = await self.db.execute(
            select(CaseAnswer).where(CaseAnswer.case_id == case_id)
        )
        return list(result.scalars().all())

class EvidenceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, case_id: UUID, **kwargs) -> Evidence:
        evidence = Evidence(case_id=case_id, **kwargs)
        self.db.add(evidence)
        await self.db.commit()
        await self.db.refresh(evidence)
        return evidence

    async def get_by_id(self, evidence_id: UUID) -> Optional[Evidence]:
        result = await self.db.execute(select(Evidence).where(Evidence.id == evidence_id))
        return result.scalar_one_or_none()

    async def get_by_case(self, case_id: UUID) -> List[Evidence]:
        result = await self.db.execute(
            select(Evidence).where(Evidence.case_id == case_id)
        )
        return list(result.scalars().all())

    async def delete(self, evidence_id: UUID) -> None:
        await self.db.execute(delete(Evidence).where(Evidence.id == evidence_id))
        await self.db.commit()

    async def update_ai_evaluation(self, evidence_id: UUID, evaluation: dict) -> None:
        await self.db.execute(
            update(Evidence).where(Evidence.id == evidence_id).values(ai_evaluation=evaluation)
        )
        await self.db.commit()

class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Document:
        doc = Document(**kwargs)
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def get_by_id(self, doc_id: UUID) -> Optional[Document]:
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def get_by_case(self, case_id: UUID) -> List[Document]:
        result = await self.db.execute(
            select(Document).where(Document.case_id == case_id)
        )
        return list(result.scalars().all())

    async def update_content(self, doc_id: UUID, content: str) -> Document:
        doc = await self.get_by_id(doc_id)
        if doc:
            doc.content = content
            doc.version = (doc.version or 0) + 1
            await self.db.commit()
            await self.db.refresh(doc)
        return doc

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, phone: str, **kwargs) -> User:
        user = User(phone=phone, **kwargs)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

class RiskAssessmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, case_id: UUID, **kwargs) -> RiskAssessment:
        assessment = RiskAssessment(case_id=case_id, **kwargs)
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment

    async def get_by_case(self, case_id: UUID) -> Optional[RiskAssessment]:
        result = await self.db.execute(
            select(RiskAssessment).where(RiskAssessment.case_id == case_id)
        )
        return result.scalar_one_or_none()
```

- [ ] **Step 5: 创建 API 路由 api/cases.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.database import get_db
from app.db.repositories import CaseRepository
from app.models.schemas import CaseCreate, CaseResponse

router = APIRouter(prefix="/api/cases", tags=["cases"])

@router.post("", response_model=CaseResponse)
async def create_case(
    _: CaseCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = CaseRepository(db)
    case = await repo.create(user_id=uuid.uuid4())  # TODO: from auth
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
```

- [ ] **Step 6: 提交数据库模型**

```bash
git add -A
git commit -m "phase 1: database models and repositories"
```

---

### Task 3: 认证 API 实现

**Files:**
- Create: `backend/app/utils/security.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/auth.py`

- [ ] **Step 1: 创建 JWT 工具 utils/security.py**

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise ValueError("Invalid token")
```

- [ ] **Step 2: 创建 Auth Service**

```python
from datetime import timedelta
from app.utils.security import create_access_token, decode_token
from app.db.repositories import UserRepository
from app.db.database import AsyncSessionLocal

class AuthService:
    @staticmethod
    async def login(phone: str, code: str) -> str:
        # 验证码校验（简化版，实际应连接短信服务）
        if code != "123456":  # TODO: 真实验证码
            raise ValueError("Invalid code")

        async with AsyncSessionLocal() as db:
            repo = UserRepository(db)
            user = await repo.get_by_phone(phone)
            if not user:
                user = await repo.create(phone=phone)
            token = create_access_token({"sub": str(user.id)})
            return token

    @staticmethod
    async def get_current_user(token: str):
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token")
        async with AsyncSessionLocal() as db:
            repo = UserRepository(db)
            user = await repo.get_by_id(UUID(user_id))
            if not user:
                raise ValueError("User not found")
            return user
```

- [ ] **Step 3: 创建 Auth API**

```python
from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    try:
        token = await AuthService.login(req.phone, req.code)
        return TokenResponse(access_token=token)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/logout")
async def logout():
    return {"status": "ok"}
```

- [ ] **Step 4: 提交认证 API**

```bash
git add -A
git commit -m "phase 1: auth API"
```

---

## Phase 2: 知识库 + AI Agent

### Task 4: RAG 检索链实现

**Files:**
- Create: `backend/app/knowledge/loader.py`
- Create: `backend/app/knowledge/embedder.py`
- Create: `backend/app/knowledge/vector_store.py`
- Create: `backend/app/chains/retrieval_chain.py`

- [ ] **Step 1: 创建知识加载器 knowledge/loader.py**

```python
import yaml
from pathlib import Path
from typing import List, Dict, Any

class KnowledgeLoader:
    def __init__(self, data_dir: str = "backend/data"):
        self.data_dir = Path(data_dir)

    def load_causes(self) -> List[Dict[str, Any]]:
        """加载案由知识"""
        causes = []
        causes_dir = self.data_dir / "causes"
        for file in causes_dir.glob("*.yaml"):
            with open(file, encoding="utf-8") as f:
                causes.append(yaml.safe_load(f))
        return causes

    def load_templates(self) -> List[Dict[str, Any]]:
        """加载文书模板"""
        templates = []
        templates_dir = self.data_dir / "templates"
        for file in templates_dir.glob("*.yaml"):
            with open(file, encoding="utf-8") as f:
                templates.append(yaml.safe_load(f))
        return templates

    def load_evidence_knowledge(self) -> List[Dict[str, Any]]:
        """加载证据知识"""
        evidence = []
        evidence_dir = self.data_dir / "evidence"
        for file in evidence_dir.glob("*.yaml"):
            with open(file, encoding="utf-8") as f:
                evidence.append(yaml.safe_load(f))
        return evidence

    def load_risk_knowledge(self) -> List[Dict[str, Any]]:
        """加载风险知识"""
        risks = []
        risks_dir = self.data_dir / "risks"
        for file in risks_dir.glob("*.yaml"):
            with open(file, encoding="utf-8") as f:
                risks.append(yaml.safe_load(f))
        return risks
```

- [ ] **Step 2: 创建 Embedder knowledge/embedder.py**

```python
from langchain_qianwen import QianwenEmbeddings
from app.config import settings

class KnowledgeEmbedder:
    def __init__(self):
        self.embeddings = QianwenEmbeddings(
            model="text-embedding-v3",
            qianwen_api_key=settings.QWEN_API_KEY
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self.embeddings.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        return self.embeddings.embed_query(query)
```

- [ ] **Step 3: 创建 Vector Store knowledge/vector_store.py**

```python
from langchain_milvus import Milvus
from app.knowledge.embedder import KnowledgeEmbedder
from app.config import settings

class VectorStoreManager:
    def __init__(self):
        self.embedder = KnowledgeEmbedder()
        self._stores = {}

    def get_store(self, collection_name: str) -> Milvus:
        if collection_name not in self._stores:
            self._stores[collection_name] = Milvus(
                embedding_function=self.embedder.embed_texts,
                connection_args={"uri": settings.MILVUS_URL},
                collection_name=collection_name,
            )
        return self._stores[collection_name]

    async def add_texts(self, collection_name: str, texts: List[str], metadatas: List[dict]):
        store = self.get_store(collection_name)
        store.add_texts(texts=texts, metadatas=metadatas)

    async def similarity_search(
        self, collection_name: str, query: str, k: int = 5
    ) -> List[tuple]:
        store = self.get_store(collection_name)
        results = store.similarity_search_with_score(query, k=k)
        return results
```

- [ ] **Step 4: 创建 RAG Chain chains/retrieval_chain.py**

```python
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
            return "\n".join([doc.page_content for doc in docs])

        chain = (
            {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
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
```

- [ ] **Step 5: 提交 RAG Chain**

```bash
git add -A
git commit -m "phase 2: RAG retrieval chain"
```

- [ ] **Step 6: 创建知识库初始化脚本 scripts/seed_knowledge.py**

```python
"""Milvus 知识库初始化脚本"""
import asyncio
from pathlib import Path
from app.knowledge.loader import KnowledgeLoader
from app.knowledge.vector_store import VectorStoreManager
from app.knowledge.embedder import KnowledgeEmbedder
from langchain_milvus import Milvus
from app.config import settings

async def seed_knowledge():
    loader = KnowledgeLoader()
    embedder = KnowledgeEmbedder()

    # 案由知识库
    causes = loader.load_causes()
    cause_texts = []
    cause_metas = []
    for cause in causes:
        text = f"案由: {cause['name']}\n编码: {cause['code']}\n问题: {cause.get('questions', [])}"
        cause_texts.append(text)
        cause_metas.append({"source": cause['code']})

    # 创建 Milvus collection 并插入
    cause_store = Milvus(
        embedding_function=embedder.embed_texts,
        connection_args={"uri": settings.MILVUS_URL},
        collection_name="causes",
    )
    cause_store.add_texts(texts=cause_texts, metadatas=cause_metas)

    # 证据知识库
    evidence = loader.load_evidence_knowledge()
    evidence_texts = []
    evidence_metas = []
    for ev in evidence:
        text = f"证据类型: {ev['name']}\n用途: {ev['purpose']}\n收集方法: {ev.get('how_to_collect', '')}"
        evidence_texts.append(text)
        evidence_metas.append({"source": ev['name']})

    evidence_store = Milvus(
        embedding_function=embedder.embed_texts,
        connection_args={"uri": settings.MILVUS_URL},
        collection_name="evidence",
    )
    evidence_store.add_texts(texts=evidence_texts, metadatas=evidence_metas)

    # 风险知识库
    risks = loader.load_risk_knowledge()
    risk_texts = []
    risk_metas = []
    for risk in risks:
        text = f"风险类型: {risk['type']}\n描述: {risk['description']}\n规避建议: {risk.get('suggestions', [])}"
        risk_texts.append(text)
        risk_metas.append({"source": risk['type']})

    risk_store = Milvus(
        embedding_function=embedder.embed_texts,
        connection_args={"uri": settings.MILVUS_URL},
        collection_name="risks",
    )
    risk_store.add_texts(texts=risk_texts, metadatas=risk_metas)

    print("Knowledge base seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_knowledge())
```

- [ ] **Step 7: 添加知识库数据示例**

创建 `backend/data/causes/欠薪.yaml`:
```yaml
name: 欠薪
code: QS-001
level: 1
common_questions:
  - id: q1
    text: 您遇到的欠薪情况属于哪种？
    type: choice
    options:
      - 未支付工资
      - 拖欠加班费
      - 拖欠奖金
      - 拖欠经济补偿金
  - id: q2
    text: 入职时间？
    type: date
special_questions:
  - id: sq1
    text: 工资支付周期是？
    type: choice
    options:
      - 月薪
      - 日薪
      - 计件
```

创建 `backend/data/evidence/劳动关系.yaml`:
```yaml
name: 劳动关系证据
purpose: 证明劳动者与用人单位存在劳动关系
items:
  - name: 劳动合同
    description: 证明劳动关系存在
    how_to_collect: 向公司HR申请复印，加盖公司公章
  - name: 社保缴费记录
    description: 证明劳动关系及时间
    how_to_collect: 登录当地社保APP导出
  - name: 工资流水
    description: 证明工资标准和发放情况
    how_to_collect: 手机银行APP导出带公司名的流水
```

创建 `backend/data/risks/时效风险.yaml`:
```yaml
type: 时效风险
description: 劳动仲裁申请时效为一年，从知道或应当知道权利被侵害之日起计算
suggestions:
  - 尽快申请仲裁，避免时效过期
  - 保存好相关证据材料
  - 如有时效中止、中断情形，准备相应证明材料
```

- [ ] **Step 8: 提交知识库初始化**

```bash
git add -A
git commit -m "phase 2: knowledge base seeding and sample data"
```

---

### Task 5: AI Agent 实现

**Files:**
- Create: `backend/app/agents/base_agent.py`
- Create: `backend/app/agents/case_analysis_agent.py`
- Create: `backend/app/agents/evidence_eval_agent.py`
- Create: `backend/app/agents/risk_assess_agent.py`
- Create: `backend/app/agents/document_gen_agent.py`
- Create: `backend/app/agents/ai_review_agent.py`
- Create: `backend/app/api/ai.py`

- [ ] **Step 1: 创建 Agent 基类 agents/base_agent.py**

```python
from abc import ABC, abstractmethod
from langchain_core.agents import AgentFinish
from typing import Dict, Any

class BaseAgent(ABC):
    def __init__(self, llm):
        self.llm = llm

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Agent"""
        pass

    def _format_output(self, result: str) -> Dict[str, Any]:
        """格式化输出"""
        return {"result": result, "status": "success"}
```

- [ ] **Step 2: 创建案情分析 Agent (ReAct) agents/case_analysis_agent.py**

```python
from langchain_qianwen import ChatQianwen
from langchain_core.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from app.agents.base_agent import BaseAgent
from app.chains.retrieval_chain import RetrievalChain
from app.config import settings
import json

class CaseAnalysisAgent(BaseAgent):
    """Step 4: 案情分析 Agent (ReAct 模式)"""

    def __init__(self):
        self.llm = ChatQianwen(
            model="qwen-turbo",
            qianwen_api_key=settings.QWEN_API_KEY,
            temperature=0.3
        )
        self.retrieval_chain = RetrievalChain()
        self._setup_tools()
        self._setup_agent()

    def _setup_tools(self):
        @tool
        def search_causes(query: str) -> str:
            """搜索相关案由信息"""
            import asyncio
            results = asyncio.get_event_loop().run_until_complete(
                self.retrieval_chain.vector_store.similarity_search(
                    "causes", query, k=3
                )
            )
            return "\n".join([doc.page_content for doc in results])

        @tool
        def search_evidence(query: str) -> str:
            """搜索证据要求"""
            import asyncio
            results = asyncio.get_event_loop().run_until_complete(
                self.retrieval_chain.vector_store.similarity_search(
                    "evidence", query, k=3
                )
            )
            return "\n".join([doc.page_content for doc in results])

        self.tools = [search_causes, search_evidence]

    def _setup_agent(self):
        template = """你是一名劳动法律师助理，帮助分析用户的劳动维权案件。

你可以使用以下工具：
- search_causes: 搜索相关案由信息
- search_evidence: 搜索证据要求

你的任务：
1. 分析用户描述的案情
2. 使用工具搜索相关案由
3. 识别涉及的案由类型
4. 生成规范的案件事实描述

请以 JSON 格式返回结果：
{{"case_description": "...", "cause_codes": [...], "confidence": 0.85}}

开始分析：{input}"""

        prompt = ChatPromptTemplate.from_template(template)
        self.agent = create_react_agent(self.llm, self.tools, prompt)

    async def run(self, input_data: dict) -> dict:
        answers = input_data.get("answers", [])
        evidence = input_data.get("evidence", [])

        # 构建案情描述
        case_text = self._build_case_text(answers)

        # ReAct 推理
        result = await self.agent.ainvoke({"input": case_text})

        # 解析结果
        return self._parse_result(result)

    def _build_case_text(self, answers: list) -> str:
        return "\n".join([
            f"问题: {a['question_id']}\n回答: {a['answer_value']}"
            for a in answers
        ])

    def _parse_result(self, result) -> dict:
        """解析 Agent 返回结果"""
        try:
            # 从 AgentFinish 中提取输出
            if hasattr(result, 'output'):
                output = result.output
            else:
                output = str(result)

            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            # 如果没有 JSON，返回默认
            return {
                "case_description": output,
                "cause_codes": [],
                "confidence": 0.5
            }
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse agent result: {e}, result: {result}")
```

- [ ] **Step 3: 创建证据审核 Agent (Chain) agents/evidence_eval_agent.py**

```python
from langchain_qianwen import ChatQianwen
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.agents.base_agent import BaseAgent
from app.config import settings

class EvidenceEvalAgent(BaseAgent):
    """Step 5: 证据审核 Agent (Chain 模式)"""

    def __init__(self):
        self.llm = ChatQianwen(
            model="qwen-turbo",
            qianwen_api_key=settings.QWEN_API_KEY,
            temperature=0.1
        )
        self._setup_chain()

    def _setup_chain(self):
        template = """你是一名证据审核专家，评估用户提交的证据是否充分。

证据信息：
- 证据名称: {evidence_name}
- 证据类型: {evidence_type}
- 用户备注: {note}

案由: {cause_codes}

请评估：
1. 证据内容是否清晰可读
2. 证据与案件的关联性
3. 证据是否充分

请以 JSON 格式返回：
{{
    "is_valid": true/false,
    "clarity_score": 0-100,
    "relevance_score": 0-100,
    "completeness_score": 0-100,
    "issues": ["问题列表"],
    "suggestions": ["改进建议"]
}}"""

        self.prompt = ChatPromptTemplate.from_template(template)
        self.chain = self.prompt | self.llm | JsonOutputParser()

    async def run(self, input_data: dict) -> dict:
        result = await self.chain.ainvoke({
            "evidence_name": input_data.get("name", ""),
            "evidence_type": input_data.get("type", ""),
            "note": input_data.get("note", ""),
            "cause_codes": input_data.get("cause_codes", [])
        })
        return result
```

- [ ] **Step 4: 创建风险评估 Agent (ReAct) agents/risk_assess_agent.py**

```python
from langchain_qianwen import ChatQianwen
from langchain_core.agents import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from app.agents.base_agent import BaseAgent
from app.chains.retrieval_chain import RetrievalChain
from app.config import settings

class RiskAssessAgent(BaseAgent):
    """Step 6: 风险评估 Agent (ReAct 模式)"""

    def __init__(self):
        self.llm = ChatQianwen(
            model="qwen-plus",
            qianwen_api_key=settings.QWEN_API_KEY,
            temperature=0.3
        )
        self.retrieval_chain = RetrievalChain()

    async def run(self, input_data: dict) -> dict:
        case_description = input_data.get("case_description", "")
        cause_codes = input_data.get("cause_codes", [])
        evidence_status = input_data.get("evidence_status", {})

        template = """作为劳动维权风险分析师，分析以下案件的风险等级。

案件描述：
{case_description}

案由：{cause_codes}

证据状态：
{evidence_status}

请识别：
1. 时效风险（如劳动仲裁时效为1年）
2. 证据风险（证据链是否完整）
3. 计算错误风险（金额计算是否正确）
4. 其他风险

返回格式（JSON）：
{{
    "risk_points": [
        {{
            "type": "时效风险",
            "level": "高/中/低",
            "description": "风险描述",
            "reason": "为什么存在此风险"
        }}
    ],
    "overall_level": "高/中/低",
    "suggestions": ["规避建议列表"]
}}"""

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm

        result = await chain.ainvoke({
            "case_description": case_description,
            "cause_codes": ",".join(cause_codes),
            "evidence_status": str(evidence_status)
        })

        return self._parse_result(result)

    def _parse_result(self, result: str) -> dict:
        import json
        import re
        try:
            # 尝试直接解析
            return json.loads(result)
        except json.JSONDecodeError:
            # 尝试从输出中提取 JSON
            json_match = re.search(r'\{.*\}', str(result), re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse risk assessment: {e}, output: {result}")
            raise ValueError(f"No JSON found in risk assessment output: {result}")
```

- [ ] **Step 5: 创建文书生成 Agent (ReAct) agents/document_gen_agent.py**

```python
from langchain_qianwen import ChatQianwen
from langchain_core.agents import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from app.agents.base_agent import BaseAgent
from app.config import settings

class DocumentGenAgent(BaseAgent):
    """Step 7: 文书生成 Agent (ReAct 模式)"""

    def __init__(self):
        self.llm = ChatQianwen(
            model="qwen-plus",
            qianwen_api_key=settings.QWEN_API_KEY,
            temperature=0.4
        )

    async def run(self, input_data: dict) -> dict:
        case_description = input_data.get("case_description", "")
        claims = input_data.get("claims", [])
        document_type = input_data.get("document_type", "仲裁申请书")

        # 将 claims 列表格式化为字符串
        claims_text = "\n".join([f"- {c}" for c in claims]) if claims else "（无具体权益清单）"

        template = f"""作为劳动仲裁文书起草专家，根据以下案件信息生成{document_type}。

案件事实：
{case_description}

仲裁请求/权益清单：
{claims_text}

请生成一份完整、规范的{document_type}，包含：
1. 当事人信息
2. 仲裁请求事项
3. 事实与理由
4. 证据清单

注意：
- 使用正式的法律用语
- 金额计算精确
- 事实描述清晰准确

直接输出文书内容，不需要额外解释。"""

        result = await self.llm.ainvoke(template)
        return {
            "content": result.content,
            "document_type": document_type
        }
```

- [ ] **Step 6: 创建 AI 复核 Agent (Chain) agents/ai_review_agent.py**

```python
from langchain_qianwen import ChatQianwen
from langchain_core.prompts import ChatPromptTemplate
from app.agents.base_agent import BaseAgent
from app.config import settings

class AIReviewAgent(BaseAgent):
    """Step 9: AI 复核 Agent (Chain 模式)"""

    def __init__(self):
        self.llm = ChatQianwen(
            model="qwen-max",
            qianwen_api_key=settings.QWEN_API_KEY,
            temperature=0.5
        )

    async def run(self, input_data: dict) -> dict:
        case_data = input_data.get("case_data", {})
        user_question = input_data.get("user_question", "请复核我的案件")

        template = """你是劳动法律专家，请复核用户的劳动维权案件。

案件信息：
{case_data}

用户问题：{question}

请提供专业的复核意见，包括：
1. 案件事实是否清晰
2. 案由选择是否正确
3. 证据是否充分
4. 仲裁请求是否合理
5. 其他建议

如果用户没有特定问题，请提供全面的案件复核。"""

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm

        result = await chain.ainvoke({
            "case_data": str(case_data),
            "question": user_question
        })

        return {"review": result.content}
```

- [ ] **Step 7: 创建 AI API 路由 api/ai.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.db.database import get_db
from app.db.repositories import CaseRepository, EvidenceRepository, DocumentRepository
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
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/ai", tags=["ai"])

@router.post("/analyze-case", response_model=CaseAnalysisResponse)
async def analyze_case(
    req: CaseAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    # 获取案件和答案数据
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(req.case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    # 获取该案件的所有回答
    from app.db.repositories import CaseAnswerRepository
    answer_repo = CaseAnswerRepository(db)
    answers = await answer_repo.get_by_case(req.case_id)
    answers_data = [
        {"question_id": a.question_id, "answer_value": a.answer_value}
        for a in answers
    ]

    agent = CaseAnalysisAgent()
    result = await agent.run({
        "case_id": str(req.case_id),
        "answers": answers_data,
        "evidence": []  # 后续从证据服务获取
    })

    # 更新案件描述和案由
    if "case_description" in result:
        await case_repo.update_description(req.case_id, result["case_description"])
    if "cause_codes" in result:
        await case_repo.update_causes(req.case_id, result["cause_codes"])

    return CaseAnalysisResponse(**result)

@router.post("/evaluate-evidence")
async def evaluate_evidence(
    req: EvidenceEvalRequest,
    db: AsyncSession = Depends(get_db)
):
    # 获取证据记录和案件上下文
    evidence_repo = EvidenceRepository(db)
    evidence = await evidence_repo.get_by_id(req.evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")

    # 获取案件案由
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

    # 更新证据的 AI 评价
    await evidence_repo.update_ai_evaluation(req.evidence_id, result)
    return result

@router.post("/risk-assessment", response_model=RiskAssessmentResponse)
async def assess_risk(
    req: RiskAssessmentRequest,
    db: AsyncSession = Depends(get_db)
):
    # 获取案件完整数据
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(req.case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    # 获取证据状态
    evidence_repo = EvidenceRepository(db)
    evidence_list = await evidence_repo.get_by_case(req.case_id)
    evidence_status = {
        "total": len(evidence_list),
        "type_a": len([e for e in evidence_list if e.type == "A"]),
        "type_b": len([e for e in evidence_list if e.type == "B"]),
        "type_c": len([e for e in evidence_list if e.type == "C"])
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
    # 获取案件数据
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(req.case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    doc_service = DocumentService()
    document = await doc_service.generate(
        case_id=req.case_id,
        document_type=req.document_type,
        case_description=case.case_description or "",
        claims=[],  # TODO: 从权益清单获取
        db=db
    )

    return {"document_id": str(document.id), "content": document.content}

@router.post("/review")
async def ai_review(case_data: dict, user_question: str = None):
    agent = AIReviewAgent()
    result = await agent.run({
        "case_data": case_data,
        "user_question": user_question
    })
    return result
```

**Note:** `CaseAnswerRepository` and `EvidenceRepository.update_ai_evaluation` need to be added to `db/repositories.py`.

- [ ] **Step 8: 提交 AI Agent**

```bash
git add -A
git commit -m "phase 2: AI agents implementation"
```

---

## Phase 3: 业务功能

### Task 6: 前端核心组件

**Files:**
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/services/aiService.ts`
- Create: `frontend/src/stores/caseStore.ts`
- Create: `frontend/src/hooks/useStep.ts`
- Create: `frontend/src/components/layout/StepWizard.tsx`
- Create: `frontend/src/components/layout/StepContent.tsx`
- Create: `frontend/src/pages/CaseWizard.tsx`

- [ ] **Step 1: 创建 API 服务 frontend/src/services/api.ts**

```typescript
import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' }
})

// Auth
export const auth = {
  login: (phone: string, code: string) =>
    client.post('/auth/login', { phone, code }),
  logout: () => client.post('/auth/logout')
}

// Cases
export const cases = {
  create: () => client.post('/cases'),
  get: (id: string) => client.get(`/cases/${id}`),
  updateStep: (id: string, step: number) =>
    client.put(`/cases/${id}/step/${step}`),
  getAnswers: (id: string) => client.get(`/cases/${id}/answers`),
  submitAnswer: (caseId: string, questionId: string, value: any) =>
    client.post(`/cases/${caseId}/answers`, { question_id: questionId, answer_value: value })
}

// Causes
export const causes = {
  list: () => client.get('/causes'),
  get: (id: string) => client.get(`/causes/${id}`),
  getQuestions: (id: string) => client.get(`/causes/${id}/questions`)
}

// Evidence
export const evidence = {
  upload: (caseId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return client.post(`/cases/${caseId}/evidence`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  list: (caseId: string) => client.get(`/cases/${caseId}/evidence`),
  delete: (id: string) => client.delete(`/evidence/${id}`)
}

// Documents
export const documents = {
  list: (caseId: string) => client.get(`/cases/${caseId}/documents`),
  get: (id: string) => client.get(`/documents/${id}`),
  export: (id: string, format: 'docx' | 'pdf') =>
    client.get(`/documents/${id}/export/${format}`, { responseType: 'blob' })
}

// AI
export const ai = {
  analyzeCase: (caseId: string) =>
    client.post('/ai/analyze-case', { case_id: caseId }),
  evaluateEvidence: (evidenceId: string) =>
    client.post('/ai/evaluate-evidence', { evidence_id: evidenceId }),
  assessRisk: (caseId: string) =>
    client.post('/ai/risk-assessment', { case_id: caseId }),
  generateDocument: (caseId: string, documentType: string) =>
    client.post('/ai/generate-document', { case_id: caseId, document_type: documentType }),
  review: (caseData: object, question?: string) =>
    client.post('/ai/review', { case_data: caseData, user_question: question })
}

export const api = { auth, cases, causes, evidence, documents, ai }
```

- [ ] **Step 2: 创建 AI 服务 frontend/src/services/aiService.ts**

```typescript
import { ai } from './api'

export const aiService = {
  analyzeCase: async (caseId: string) => {
    const response = await ai.analyzeCase(caseId)
    return response.data
  },

  evaluateEvidence: async (evidenceId: string) => {
    const response = await ai.evaluateEvidence(evidenceId)
    return response.data
  },

  assessRisk: async (caseId: string) => {
    const response = await ai.assessRisk(caseId)
    return response.data
  },

  generateDocument: async (caseId: string, documentType: string = '仲裁申请书') => {
    const response = await ai.generateDocument(caseId, documentType)
    return response.data
  },

  review: async (caseData: object, question?: string) => {
    const response = await ai.review(caseData, question)
    return response.data
  }
}
```

- [ ] **Step 3: 创建 Zustand Store stores/caseStore.ts**

```typescript
import { create } from 'zustand'

interface CaseState {
  caseId: string | null
  currentStep: number
  status: 'idle' | 'loading' | 'success' | 'error'
  caseData: any | null
  setCaseId: (id: string) => void
  setStep: (step: number) => void
  setCaseData: (data: any) => void
  reset: () => void
}

export const useCaseStore = create<CaseState>((set) => ({
  caseId: null,
  currentStep: 1,
  status: 'idle',
  caseData: null,
  setCaseId: (id) => set({ caseId: id }),
  setStep: (step) => set({ currentStep: Math.min(9, Math.max(1, step)) }),
  setCaseData: (data) => set({ caseData: data }),
  reset: () => set({ caseId: null, currentStep: 1, status: 'idle', caseData: null })
}))
```

- [ ] **Step 2: 创建步骤管理 Hook hooks/useStep.ts**

```typescript
import { useCaseStore } from '../stores/caseStore'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../services/api'

export function useStep() {
  const { caseId, currentStep, setStep } = useCaseStore()

  const stepLabels = [
    '模式选择', '问题初判', '信息补全', '案件定性',
    '证据攻略', '风险提示', '文书生成', '行动路线图', '求助复核'
  ]

  const goToStep = async (step: number) => {
    if (!caseId) return
    await api.updateCaseStep(caseId, step)
    setStep(step)
  }

  const nextStep = () => goToStep(currentStep + 1)
  const prevStep = () => goToStep(currentStep - 1)

  return {
    currentStep,
    stepLabels,
    goToStep,
    nextStep,
    prevStep,
    canGoNext: currentStep < 9,
    canGoPrev: currentStep > 1
  }
}
```

- [ ] **Step 3: 创建步骤向导组件 layout/StepWizard.tsx**

```tsx
import React from 'react'
import { useStep } from '../../hooks/useStep'
import styles from './StepWizard.module.css'

export function StepWizard() {
  const { currentStep, stepLabels, goToStep } = useStep()

  return (
    <div className={styles.wizard}>
      <div className={styles.steps}>
        {stepLabels.map((label, index) => {
          const stepNum = index + 1
          const isActive = stepNum === currentStep
          const isCompleted = stepNum < currentStep

          return (
            <React.Fragment key={stepNum}>
              <button
                className={`${styles.step} ${isActive ? styles.active : ''} ${isCompleted ? styles.completed : ''}`}
                onClick={() => goToStep(stepNum)}
                disabled={stepNum > currentStep}
              >
                <span className={styles.stepNumber}>{stepNum}</span>
                <span className={styles.stepLabel}>{label}</span>
              </button>
              {index < stepLabels.length - 1 && (
                <div className={`${styles.connector} ${isCompleted ? styles.connectorCompleted : ''}`} />
              )}
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 创建步骤内容容器 components/layout/StepContent.tsx**

```tsx
import React from 'react'
import { CauseSelector } from '../business/CauseSelector'
import { QuestionCard } from '../business/QuestionCard'
import { EvidenceUploader } from '../business/EvidenceUploader'
import { EvidenceStatusBoard } from '../business/EvidenceStatusBoard'
import { AmountCalculator } from '../business/AmountCalculator'
import { DocumentPreview } from '../business/DocumentPreview'
import { RoadmapFlow } from '../business/RoadmapFlow'
import { AIChatPanel } from '../ai/AIChatPanel'
import { AIFeedbackCard } from '../ai/AIFeedbackCard'
import { useCaseStore } from '../../stores/caseStore'

interface StepContentProps {
  step: number
}

export function StepContent({ step }: StepContentProps) {
  const { caseId } = useCaseStore()

  const renderStep = () => {
    switch (step) {
      case 1:
        return <CauseSelector />
      case 2:
      case 3:
        return <QuestionCard step={step} />
      case 4:
        return (
          <div>
            <AIFeedbackCard title="案情分析" />
            <button onClick={() => api.analyzeCase(caseId)}>开始 AI 分析</button>
          </div>
        )
      case 5:
        return (
          <div>
            <EvidenceStatusBoard caseId={caseId} />
            <EvidenceUploader caseId={caseId} />
          </div>
        )
      case 6:
        return <AIFeedbackCard title="风险评估" />
      case 7:
        return <DocumentPreview caseId={caseId} />
      case 8:
        return <RoadmapFlow />
      case 9:
        return <AIChatPanel caseId={caseId} />
      default:
        return <div>未知步骤</div>
    }
  }

  return <div className="step-content">{renderStep()}</div>
}
```

- [ ] **Step 5: 创建案件引导页面 pages/CaseWizard.tsx**

```tsx
import React from 'react'
import { StepWizard } from '../components/layout/StepWizard'
import { StepContent } from '../components/layout/StepContent'
import { useCaseStore } from '../stores/caseStore'
import { Button } from '../components/ui/Button'
import { useStep } from '../hooks/useStep'

export function CaseWizard() {
  const { currentStep, nextStep, prevStep, canGoNext, canGoPrev } = useStep()
  const { status } = useCaseStore()

  return (
    <div className={styles.container}>
      <StepWizard />

      <div className={styles.content}>
        <StepContent step={currentStep} />
      </div>

      <div className={styles.navigation}>
        {canGoPrev && (
          <Button variant="secondary" onClick={prevStep}>
            上一步
          </Button>
        )}
        {canGoNext && (
          <Button variant="primary" onClick={nextStep} disabled={status === 'loading'}>
            下一步
          </Button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: 提交前端核心组件**

```bash
git add -A
git commit -m "phase 3: frontend core components"
```

---

### Task 7: 证据管理和文书功能

**Files:**
- Create: `frontend/src/components/business/EvidenceUploader.tsx`
- Create: `frontend/src/components/business/EvidenceStatusBoard.tsx`
- Create: `frontend/src/components/business/DocumentPreview.tsx`
- Modify: `backend/app/api/documents.py`
- Modify: `backend/app/api/evidence.py`

- [ ] **Step 1: 创建证据上传组件**

```tsx
import React, { useState } from 'react'
import { api } from '../../services/api'
import styles from './EvidenceUploader.module.css'

interface EvidenceUploaderProps {
  caseId: string
  onUploadComplete?: () => void
}

export function EvidenceUploader({ caseId, onUploadComplete }: EvidenceUploaderProps) {
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const handleUpload = async (files: FileList) => {
    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        await api.uploadEvidence(caseId, file)
      }
      onUploadComplete?.()
    } finally {
      setUploading(false)
    }
  }

  return (
    <div
      className={`${styles.uploader} ${dragOver ? styles.dragOver : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragOver(false)
        handleUpload(e.dataTransfer.files)
      }}
    >
      <input
        type="file"
        multiple
        accept="image/*,.pdf"
        onChange={(e) => e.target.files && handleUpload(e.target.files)}
        className={styles.input}
      />
      <div className={styles.content}>
        <span className={styles.icon}>📎</span>
        <span className={styles.text}>
          {uploading ? '上传中...' : '点击或拖拽上传证据'}
        </span>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 创建证据状态看板**

```tsx
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../services/api'
import styles from './EvidenceStatusBoard.module.css'

interface EvidenceStatusBoardProps {
  caseId: string
}

const statusColors = {
  A: 'green',  // 已有
  B: 'yellow', // 可补充
  C: 'red'     // 无法取得
}

export function EvidenceStatusBoard({ caseId }: EvidenceStatusBoardProps) {
  const { data: evidenceList, refetch } = useQuery({
    queryKey: ['evidence', caseId],
    queryFn: () => api.getEvidence(caseId)
  })

  const getCompletenessLevel = () => {
    if (!evidenceList?.length) return '严重缺乏'
    const typeACount = evidenceList.filter(e => e.type === 'A').length
    const total = evidenceList.length
    const ratio = typeACount / total
    if (ratio >= 0.8) return '充分'
    if (ratio >= 0.5) return '不完整'
    if (ratio >= 0.2) return '缺乏'
    return '严重缺乏'
  }

  return (
    <div className={styles.board}>
      <div className={styles.header}>
        <h3>证据清单</h3>
        <span className={`${styles.level} ${styles[getCompletenessLevel()]}`}>
          {getCompletenessLevel()}
        </span>
      </div>

      <div className={styles.list}>
        {evidenceList?.map((evidence) => (
          <div key={evidence.id} className={styles.item}>
            <span
              className={`${styles.badge} ${styles[statusColors[evidence.type]]}`}
            >
              {evidence.type}
            </span>
            <span className={styles.name}>{evidence.name}</span>
            {evidence.ai_evaluation && (
              <span className={styles.score}>
                {evidence.ai_evaluation.completeness_score}%
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: 创建文书预览组件**

```tsx
import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../services/api'
import { Button } from '../ui/Button'
import styles from './DocumentPreview.module.css'

interface DocumentPreviewProps {
  caseId: string
}

export function DocumentPreview({ caseId }: DocumentPreviewProps) {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null)

  const { data: documents } = useQuery({
    queryKey: ['documents', caseId],
    queryFn: () => api.getDocuments(caseId)
  })

  const handleExport = async (docId: string, format: 'docx' | 'pdf') => {
    await api.exportDocument(docId, format)
  }

  return (
    <div className={styles.preview}>
      <div className={styles.sidebar}>
        <h3>文书列表</h3>
        {documents?.map((doc) => (
          <button
            key={doc.id}
            className={`${styles.docItem} ${selectedDoc === doc.id ? styles.selected : ''}`}
            onClick={() => setSelectedDoc(doc.id)}
          >
            {doc.type}
          </button>
        ))}
      </div>

      <div className={styles.content}>
        {selectedDoc ? (
          <>
            <div className={styles.toolbar}>
              <Button onClick={() => handleExport(selectedDoc, 'docx')}>
                导出 Word
              </Button>
              <Button onClick={() => handleExport(selectedDoc, 'pdf')}>
                导出 PDF
              </Button>
            </div>
            <div className={styles.document}>
              {documents?.find(d => d.id === selectedDoc)?.content}
            </div>
          </>
        ) : (
          <div className={styles.placeholder}>请选择一份文书</div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 创建证据 API 路由 api/evidence.py**

```python
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.repositories import EvidenceRepository
from app.models.schemas import EvidenceCreate, EvidenceResponse
from app.utils.file_storage import save_file

router = APIRouter(prefix="/api/cases", tags=["evidence"])

@router.post("/{case_id}/evidence", response_model=EvidenceResponse)
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # 保存文件
    file_url = await save_file(file, case_id)

    # 创建证据记录
    repo = EvidenceRepository(db)
    evidence = await repo.create(
        case_id=case_id,
        name=file.filename,
        file_url=file_url,
        type="A"  # 默认已有
    )
    return evidence

@router.get("/{case_id}/evidence", response_model=list[EvidenceResponse])
async def get_evidence(case_id: str, db: AsyncSession = Depends(get_db)):
    repo = EvidenceRepository(db)
    evidence_list = await repo.get_by_case(case_id)
    return evidence_list

@router.delete("/evidence/{evidence_id}")
async def delete_evidence(evidence_id: str, db: AsyncSession = Depends(get_db)):
    repo = EvidenceRepository(db)
    await repo.delete(evidence_id)
    return {"status": "ok"}
```

- [ ] **Step 5: 提交证据管理和文书功能**

```bash
git add -A
git commit -m "phase 3: evidence management and document features"
```

- [ ] **Step 6: 创建文书服务 backend/app/services/document_service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from uuid import UUID
from app.db.repositories import CaseRepository, DocumentRepository
from app.agents.document_gen_agent import DocumentGenAgent
from app.models.entities import Document
from typing import List

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
            content=result.get("content", ""),
            status="草稿"
        )

        return document

    async def get_by_case(self, case_id: UUID, db: AsyncSession) -> List[Document]:
        doc_repo = DocumentRepository(db)
        return await doc_repo.get_by_case(case_id)

    async def update_content(
        self,
        doc_id: UUID,
        content: str,
        db: AsyncSession
    ) -> Document:
        doc_repo = DocumentRepository(db)
        return await doc_repo.update_content(doc_id, content)
```

**Note:** `DocumentRepository` is already defined in `db/repositories.py`. No need to redefine it here.
        return await self.get_by_id(doc_id)

    async def get_by_id(self, doc_id: str) -> Document:
        from uuid import UUID
        result = await self.db.execute(
            select(Document).where(Document.id == UUID(doc_id))
        )
        return result.scalar_one()
```

- [ ] **Step 7: 提交文书服务**

```bash
git add -A
git commit -m "phase 3: document service implementation"
```

---

## Phase 4: 完善 + 部署

### Task 8: 风险评估模块

**Files:**
- Create: `backend/app/services/risk_service.py`
- Modify: `backend/app/api/ai.py`

- [ ] **Step 1: 创建风险服务 services/risk_service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repositories import CaseRepository, RiskAssessmentRepository
from app.agents.risk_assess_agent import RiskAssessAgent
from app.models.entities import RiskLevel

class RiskService:
    def __init__(self):
        self.agent = RiskAssessAgent()

    async def assess(self, case_id: str, db: AsyncSession) -> dict:
        # 获取案件信息
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(case_id)
        if not case:
            raise ValueError("Case not found")

        # 调用 AI Agent 评估
        result = await self.agent.run({
            "case_description": case.case_description,
            "cause_codes": case.cause_codes or [],
            "evidence_status": await self._get_evidence_status(case_id, db)
        })

        # 保存评估结果
        risk_repo = RiskAssessmentRepository(db)
        assessment = await risk_repo.create(
            case_id=case_id,
            risk_points=result.get("risk_points", []),
            overall_level=RiskLevel(result.get("overall_level", "中")),
            suggestions=result.get("suggestions", [])
        )

        return assessment

    async def _get_evidence_status(self, case_id: str, db: AsyncSession) -> dict:
        from app.db.repositories import EvidenceRepository
        repo = EvidenceRepository(db)
        evidence = await repo.get_by_case(case_id)
        return {
            "total": len(evidence),
            "type_a": len([e for e in evidence if e.type == "A"]),
            "type_b": len([e for e in evidence if e.type == "B"]),
            "type_c": len([e for e in evidence if e.type == "C"])
        }
```

- [ ] **Step 2: 提交风险评估模块**

```bash
git add -A
git commit -m "phase 4: risk assessment module"
```

---

### Task 9: Docker 部署配置

**Files:**
- Create: `frontend/Dockerfile`
- Create: `backend/Dockerfile`
- Create: `nginx.conf`

- [ ] **Step 1: 创建前端 Dockerfile**

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 2: 创建后端 Dockerfile**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 创建 nginx.conf**

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 4: 提交部署配置**

```bash
git add -A
git commit -m "phase 4: docker deployment configuration"
```

---

## 验收测试

### 功能验收

| 阶段 | 验收条件 |
|------|---------|
| Phase 1 | API 启动成功，数据库连接正常，JWT 认证可用 |
| Phase 2 | RAG 检索返回结果，5 个 Agent 均可调用 |
| Phase 3 | 9 步流程可正常流转，证据上传成功，文书生成成功 |
| Phase 4 | 风险评估返回结果，Docker 部署成功 |

### 端到端测试场景

```bash
# 1. 创建案件
curl -X POST http://localhost:8000/api/cases

# 2. 提交答案
curl -X POST http://localhost:8000/api/cases/{id}/answers \
  -H "Content-Type: application/json" \
  -d '{"question_id": "q1", "answer_value": "欠薪"}'

# 3. AI 分析案情
curl -X POST http://localhost:8000/api/ai/analyze-case \
  -d '{"case_id": "{id}"}'

# 4. 上传证据
curl -X POST http://localhost:8000/api/cases/{id}/evidence \
  -F "file=@test.png"

# 5. 生成文书
curl -X POST http://localhost:8000/api/ai/generate-document \
  -d '{"case_id": "{id}", "document_type": "仲裁申请书"}'
```

---

## 实施顺序

1. **Phase 1 → Task 1-3**: 基础框架（1-2 天）
2. **Phase 2 → Task 4-5**: 知识库 + AI Agent（2-3 天）
3. **Phase 3 → Task 6-7**: 前端 + 业务功能（3-4 天）
4. **Phase 4 → Task 8-9**: 风险评估 + 部署（1-2 天）

**预计总工期**: 7-11 天

---

*计划版本: v1.0*
*生成日期: 2026-04-14*
