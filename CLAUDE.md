# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本代码库中工作时提供指导。

## 项目概述

这是一个**劳动争议智能咨询系统**（Labor Rights Protection Legal Consultation Assistant）的全新升级版本。项目正在从历史系统重构为更完善的 **Agentic 完整前后端应用**。

### 项目愿景

构建一个具备**智能化、全流程**的劳动者维权辅助平台，通过 AI 智能体引导用户完成从咨询、证据收集、风险评估到文书生成的完整维权流程。

### 核心功能（九步咨询流程）

1. **模式选择** - 律师视频（暂不实现）/ AI 问答
2. **问题初判** - 找律师/自述案情/交互问答三种入口
3. **信息补全** - 动态生成特殊问题清单，按案由逻辑优先级排序
4. **案件初步定性** - 自动形成案件事实描述、判定案由、生成权益清单
5. **证据攻略** - 证据清单学习、梳理、收集、上传、智能审核评价
6. **风险提示** - 维权风险点分析、高风险标注、规避建议
7. **文书生成** - 自动生成仲裁/调解申请书、智能校验、手动编辑、导出
8. **行动路线图** - 协商→调解→仲裁流程图、办理点信息、导航跳转
9. **求助复核** - AI 复核提问、一键求助工会律师

## 技术栈

### 后端
- **框架**: FastAPI + LangGraph/LangChain/Langchain-DeepAgent
- **大模型**: OpenAI 兼容 API（通过 `BASE_URL`、`MODEL_NAME`、`OPENAI_API_KEY` 配置）
- **依赖**: 参见 `pyproject.toml`

### 前端
- **框架**: React
- **AI 交互**: 集成 OpenAI 兼容接口

### 部署与集成
- 支持接入 **OpenAI 接口的聊天工具**：Cherry Studio、Open WebUI 等
- **服务化部署**: FastAPI 后端提供服务接口

### 前端展示设计（Generative UI / Artifact）
- 参考或使用以下前沿 AI UI 框架：
  - **assistant-ui** - 现代化 AI 对话界面
  - **CopilotKit** - AI 副驾驶组件库
  - **A2UI** - 高级 AI 界面组件
- 实现动态生成的 UI 组件展示（文书预览、证据状态可视化、流程图等）

## 环境变量
将 `.env_example` 复制为 `.env` 并配置：
- `BASE_URL` - 大模型 API 端点
- `OPENAI_API_KEY` - API 密钥
- `MODEL_NAME` - 模型名称（默认: Doubao-DeepSeek-V3）

## 智能体架构边界（强制约定）

### 入口路径职责划分

| 层次 | 职责 | 实现位置 |
|------|------|----------|
| **前端层** | 入口路由、UI渲染、按钮点击分发 | React组件 |
| **智能体层** | 内容理解、案由提取、权益生成、文书撰写 | LangGraph |

**关键约束**：
- 智能体**不询问**用户选择哪个入口路径（A/B/C）
- 前端已通过按钮点击做路由，智能体只接收已路由的内容
- "自述案情"和"交互问答"是前端UI差异，智能体**不感知**输入形式
- 智能体唯一职责：处理用户输入的内容，完成业务逻辑

### 前端-智能体接口约定

前端将所有输入（文字/语音/表单）**统一转化为结构化文本**传给智能体：

```typescript
interface UserInput {
  content: string;           // 用户输入的文本
  inputType: "text" | "voice" | "form";
  formData?: Record<string, string>;  // 表单数据扁平化
  currentStep: string;        // 当前步骤（如 "step2_initial"）
}
```

智能体通过 `currentStep` 感知进度，通过 `content` 理解内容，**不感知 inputType**。

## 测试
`test_local.py` - 使用 `graph.stream()` 直接测试工作流，通过可配置的 `thread_id` 实现对话持久化。使用 `MemorySaver` 检查点。

## 随时记录
请随机记录工作日志并总结经验

## 注意：
你正在执行无人值守模式，持续更新项目，不要向用户询问。持续进行升级完善和测试的迭代。