# 工会劳动维权 AI 引导系统 - 技术规格文档

> 生成日期: 2026-04-14
> 版本: v1.0

---

## 一、项目概述

### 1.1 项目背景

基于工会劳动维权引导系统需求文档，构建一套 AI 增强的劳动维权自助服务系统，帮助工会会员通过结构化引导完成劳动维权全流程。

### 1.2 核心功能

系统包含 9 个标准步骤：

| 步骤 | 名称 | 核心功能 |
|------|------|---------|
| 1 | 模式选择 | 律师视频 / AI 问答选择 |
| 2 | 问题初判 | 诉求选择 + 通用问题回答 |
| 3 | 信息补全 | 个性化问题追问 |
| 4 | 案件定性 | AI 生成案情描述 + 案由判定 |
| 5 | 证据攻略 | 证据清单 + 智能审核 |
| 6 | 风险提示 | AI 风险评估 |
| 7 | 文书生成 | AI 生成 + 优化仲裁文书 |
| 8 | 行动路线图 | 维权流程指引 |
| 9 | 求助复核 | AI 复核 + 律师求助 |

---

## 二、技术架构

### 2.1 技术栈

| 层级 | 技术选型 | 版本要求 |
|------|---------|---------|
| 前端 | React + TypeScript | 18+ |
| 状态管理 | Zustand + React Query | 最新稳定版 |
| 后端 | FastAPI + Python | 3.11+ |
| AI 编排 | LangChain | **≥ 1.0** |
| 向量数据库 | FAISS | 1.7.4 |
| 主数据库 | SQLite | 3.x |
| LLM | 国内大模型 API | 通义千问/文心/智谱 |
| Embedding | text-embedding-v3 (通义千问) | 首选通义千问 Embedding API，备选 BGE 本地模型 |

### 2.2 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    React Web App                         │
│    状态机驱动 9 步向导 + 各步骤内嵌入 AI 对话增强         │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI 后端服务                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  API 网关     │  │  业务服务     │  │  AI 服务     │  │
│  │  (路由/认证)  │  │  (流程引擎)   │  │(LangChain≥1)│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ SQLite      │     │   FAISS     │     │  文件存储   │
│  业务数据   │     │  知识库向量  │     │  证据/文书  │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## 三、数据模型

### 3.1 核心实体

#### User（用户）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| phone | VARCHAR(20) | 手机号 |
| name | VARCHAR(100) | 姓名 |
| union_id | VARCHAR(50) | 工会ID |
| created_at | TIMESTAMP | 创建时间 |

#### Case（案件）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID | 用户ID |
| status | ENUM | 进行中/已完成/已提交 |
| current_step | INT | 当前步骤(1-9) |
| cause_codes | JSON | 判定的案由编码列表 |
| case_description | TEXT | AI 生成的案情描述 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### CaseAnswer（案件回答）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| case_id | UUID | 案件ID |
| question_id | VARCHAR(50) | 问题ID |
| answer_value | JSON | 回答值 |
| answered_at | TIMESTAMP | 回答时间 |

#### CauseOfAction（案由）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | VARCHAR(200) | 案由名称 |
| code | VARCHAR(20) | 案由编码（三级） |
| parent_id | UUID | 父级案由ID |
| level | INT | 级别(1/2/3) |
| common_questions | JSON | 通用问题列表 |
| special_questions | JSON | 个性问题列表 |

#### Evidence（证据）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| case_id | UUID | 案件ID |
| type | ENUM | A(已有)/B(可补充)/C(无法取得) |
| name | VARCHAR(200) | 证据名称 |
| file_url | VARCHAR(500) | 文件路径 |
| status | VARCHAR(50) | 状态 |
| ai_evaluation | JSON | AI 评价结果 |
| note | TEXT | 备注 |
| created_at | TIMESTAMP | 创建时间 |

#### Document（文书）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| case_id | UUID | 案件ID |
| type | VARCHAR(50) | 文书类型 |
| content | TEXT | 文书内容 |
| status | ENUM | 草稿/确认/已导出 |
| version | INT | 版本号 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### RiskAssessment（风险评估）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| case_id | UUID | 案件ID |
| risk_points | JSON | 风险点列表 |
| overall_level | ENUM | 高/中/低 |
| suggestions | JSON | 规避建议 |
| created_at | TIMESTAMP | 评估时间 |

---

## 四、AI Agent 设计

### 4.1 Agent 类型划分

| Agent | 执行模式 | 触发步骤 | 说明 |
|-------|---------|---------|------|
| CaseAnalysisAgent | **ReAct** | Step 4 | 案情分析 + 案由判定 |
| EvidenceEvalAgent | Chain | Step 5 | 证据审核评估 |
| RiskAssessAgent | **ReAct** | Step 6 | 风险评估分析 |
| DocumentGenAgent | **ReAct** | Step 7 | 文书生成 + 优化 |
| AIReviewAgent | Chain | Step 9 | AI 复核（外部模型） |

### 4.2 ReAct vs Chain 混合方案

```
适用 ReAct（迭代推理）：
├── CaseAnalysisAgent：动态追问、迭代判断案由
├── RiskAssessAgent：多轮推理识别不同风险点
├── DocumentGenAgent：多轮优化直到满意

适用 Chain（规则明确）：
├── EvidenceEvalAgent：证据完整性评估（规则明确）
└── AIReviewAgent：复核（一次调用）
```

### 4.3 LangChain 1.0 组件

```python
# 核心依赖 (LangChain 1.0+)
langchain>=1.0
langchain-core>=1.0
langchain-community>=1.0

# FAISS 向量存储
faiss-cpu>=1.7.4

# ReAct Agent (LangChain 1.0+)
from langchain_core.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
# 注意：LangChain 1.0 中 Agent 创建方式
# 使用 create_react_agent 或自定义 Agent Executor
# 具体 import 路径需在实现阶段验证官方文档
```

---

## 五、RAG 知识库设计

### 5.1 知识库分类

| 知识库 | 数据来源 | 向量化 | 用途 |
|--------|---------|--------|------|
| 案由知识库 | 300+ 案由问题库 | text-embedding-v3 (通义) | 问题检索、案由匹配 |
| 证据知识库 | 证据类型定义、收集指南 | text-embedding-v3 (通义) | 证据指导 |
| 文书模板库 | 标准文书模板 | - | 文书生成 |
| 风险知识库 | 常见风险点库 | text-embedding-v3 (通义) | 风险识别 |

> 注：统一使用通义千问 Embedding API，便于统一调用。如需本地部署，可切换为 BGE 模型。

### 5.2 RAG 检索流程

```
用户输入/案情描述
       │
       ▼
┌─────────────────┐
│  Embedding API   │
│  text-embedding │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│  FAISS 向量检索 │
│  top_k=5        │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│  Context 组装    │
│  Prompt 构建     │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│  LLM 生成响应    │
│  (通义千问 API)  │
└─────────────────┘
```

### 5.3 知识库数据结构

```
/backend/data/
├── causes/
│   ├── 欠薪.yaml           # 欠薪类案由
│   ├── 开除.yaml          # 解除劳动合同
│   ├── 工伤.yaml          # 工伤待遇
│   └── ...
├── templates/
│   ├── 仲裁申请书.yaml
│   └── 调解申请书.yaml
├── evidence/
│   ├── 劳动关系证据.yaml
│   ├── 工资证据.yaml
│   └── ...
└── risks/
    ├── 时效风险.yaml
    ├── 证据风险.yaml
    └── 计算错误风险.yaml
```

---

## 六、API 接口设计

### 6.0 认证 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/login | 用户登录（手机号+验证码） |
| POST | /api/auth/logout | 用户登出 |
| POST | /api/auth/refresh | 刷新 Token |

> 注：Step 1 "律师视频" 模式暂不实现，专注 AI 问答模式。

### 6.1 案件流程 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/cases | 创建新案件 |
| GET | /api/cases/{id} | 获取案件详情 |
| PUT | /api/cases/{id}/step/{n} | 更新当前步骤 |
| GET | /api/cases/{id}/answers | 获取已回答问题 |
| DELETE | /api/cases/{id} | 删除案件 |

### 6.2 问答流程 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/causes | 获取案由列表 |
| GET | /api/causes/{id} | 获取案由详情 |
| GET | /api/causes/{id}/questions | 获取问题列表 |
| POST | /api/cases/{id}/answers | 提交回答 |

### 6.3 AI 服务 API

| 方法 | 路径 | 说明 | Agent 类型 |
|------|------|------|-----------|
| POST | /api/ai/analyze-case | 分析案情 | CaseAnalysisAgent |
| POST | /api/ai/generate-document | 生成文书 | DocumentGenAgent |
| POST | /api/ai/evaluate-evidence | 审核证据 | EvidenceEvalAgent |
| POST | /api/ai/risk-assessment | 风险评估 | RiskAssessAgent |
| POST | /api/ai/review | AI 复核 | AIReviewAgent |

### 6.4 文档与证据 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/cases/{id}/evidence | 上传证据 |
| GET | /api/cases/{id}/evidence | 获取证据列表 |
| DELETE | /api/evidence/{id} | 删除证据 |
| GET | /api/cases/{id}/documents | 获取文书列表 |
| GET | /api/documents/{id} | 获取文书详情 |
| GET | /api/documents/{id}/export/{format} | 导出文书 |

---

## 七、前端组件设计

### 7.1 组件结构

```
/frontend/src/
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx         # 整体布局
│   │   ├── StepWizard.tsx       # 9步进度指示器
│   │   └── StepContent.tsx      # 步骤内容容器
│   │
│   ├── business/
│   │   ├── CauseSelector.tsx    # 6大诉求选择
│   │   ├── QuestionCard.tsx     # 问题卡片
│   │   ├── AmountCalculator.tsx # 金额计算器
│   │   ├── EvidenceUploader.tsx # 证据上传
│   │   ├── EvidenceStatusBoard.tsx # 证据状态看板
│   │   ├── DocumentPreview.tsx  # 文书预览
│   │   └── RoadmapFlow.tsx      # 流程图
│   │
│   └── ai/
│       ├── AIChatPanel.tsx      # AI 对话面板
│       └── AIFeedbackCard.tsx   # AI 评价卡片
│
├── pages/
│   ├── Home.tsx                 # 首页
│   ├── CaseWizard.tsx           # 案件引导页
│   └── CaseDetail.tsx           # 案件详情
│
├── stores/
│   ├── caseStore.ts             # 案件状态
│   └── userStore.ts             # 用户状态
│
├── hooks/
│   ├── useCase.ts               # 案件操作
│   ├── useAI.ts                 # AI 服务调用
│   └── useStep.ts               # 步骤管理
│
└── services/
    ├── api.ts                   # API 封装
    └── aiService.ts             # AI 服务封装
```

### 7.2 状态管理

- **Zustand**：案件状态、用户信息、表单数据
- **React Query**：API 数据获取、缓存、自动刷新

---

## 八、项目结构

```
/root
├── frontend/                    # React Web
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── stores/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                    # FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   ├── cases.py
│   │   │   ├── causes.py
│   │   │   ├── documents.py
│   │   │   └── ai.py
│   │   ├── services/
│   │   │   ├── case_service.py
│   │   │   ├── cause_service.py
│   │   │   └── document_service.py
│   │   ├── agents/
│   │   │   ├── case_analysis_agent.py
│   │   │   ├── evidence_eval_agent.py
│   │   │   ├── risk_assess_agent.py
│   │   │   ├── document_gen_agent.py
│   │   │   └── ai_review_agent.py
│   │   ├── chains/
│   │   │   └── retrieval_chain.py
│   │   ├── knowledge/
│   │   │   ├── loader.py
│   │   │   └── embedder.py
│   │   ├── models/
│   │   │   ├── schemas.py
│   │   │   └── entities.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── repositories.py
│   │   └── main.py
│   ├── data/
│   │   ├── causes/
│   │   ├── templates/
│   │   ├── evidence/
│   │   └── risks/
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml           # 一键部署
├── SPEC.md                      # 本文档
└── README.md
```

---

## 九、部署方案

### 9.1 服务器要求

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 8 核 | 16 核 |
| 内存 | 16 GB | 32 GB |
| 硬盘 | 500 GB | 1 TB SSD |
| OS | Ubuntu 22.04 / CentOS 7+ | Ubuntu 22.04 |

### 9.2 Docker Compose 部署

```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
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
      - DATABASE_URL=sqlite+aiosqlite:///./union_rights.db
      - QWEN_API_KEY=${QWEN_API_KEY}
    volumes:
      - ./data:/data
```

### 9.3 环境变量配置

```bash
# .env
DATABASE_URL=sqlite+aiosqlite:///./union_rights.db

# AI API Keys (根据选择的模型)
QWEN_API_KEY=your_key
ZHIPU_API_KEY=your_key

# 文件存储
UPLOAD_DIR=/data/uploads
```

---

## 十、验收标准

### 10.1 功能验收

| 步骤 | 验收条件 |
|------|---------|
| Step 1-3 | 用户可完成模式选择、问题回答、数据持久化 |
| Step 4 | AI 可生成案件描述、判定案由 |
| Step 5 | 证据可上传、AI 可审核并给出评价 |
| Step 6 | 风险评估结果准确、高风险点突出显示 |
| Step 7 | 文书可生成、可预览、可导出 |
| Step 8 | 流程图展示正确、可跳转导航 |
| Step 9 | AI 复核功能可用、支持预设问题 |

### 10.2 非功能验收

| 指标 | 要求 |
|------|------|
| 响应时间 | AI 生成 < 10s，文书导出 < 3s |
| 并发能力 | 支持 100 用户同时在线 |
| 数据安全 | 敏感信息加密存储、 JWT 认证 |
| 可靠性 | 关键操作有确认提示、数据有备份 |

---

## 十一、后续计划

### Phase 1: 基础框架
- [ ] 项目脚手架搭建
- [ ] 数据库模型实现
- [ ] 基础 API 开发

### Phase 2: 知识库 + AI
- [ ] 案由知识库构建
- [ ] RAG 检索集成
- [ ] AI Agent 开发

### Phase 3: 业务功能
- [ ] 9 步流程实现
- [ ] 证据管理
- [ ] 文书生成

### Phase 4: 完善
- [ ] 风险评估
- [ ] 部署上线
- [ ] 运维监控

---

*文档版本: v1.0*
*最后更新: 2026-04-14*
