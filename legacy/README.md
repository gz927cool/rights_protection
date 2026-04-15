# 旧版本遗留代码

本目录存放项目重构前的旧版本代码，保留供历史参考。

## 移动时间
2026-04-15

## 移动原因
项目根据 `docs/二期需求.md` 进行重构，旧版本代码归档至此。

## 文件说明

### `service.py`
- 旧版 FastAPI 服务入口（端口 7777）
- 路由前缀：`/agent-ai-weiquan/v1/chat/completions`
- 使用 `legal_supervisor.py` 中的 supervisor agent 架构
- 已被 `main.py`（九步咨询系统）取代

### `langgraph_model/legal_assistant.py`
- 旧版多智能体系统
- 包含：answerer（解答）、summarizer（总结）、detailer（细节补充）、advisor（处置建议）节点
- 被 `consultation_graph.py` 的九步流程取代

### `langgraph_model/legal_supervisor.py`
- 旧版 supervisor agent 架构
- 包含 `create_extractor_graph()` 和 `create_summarizer_graph()`
- 为 `service.py` 提供路由和任务分配能力

### `langgraph_model/legal_workflow.py`
- 旧版工作流定义
- 定义 extractor 和 summarizer 节点
- 被新的 consultation_graph 架构取代

### `TEST_REPORT.md`
- 旧版流式响应测试报告
- 记录了九步系统流式接口的调试过程

### `test_sse_result.md`
- 旧版 SSE 端点测试结果
- 已过时的测试输出

### `backend/`（已删除）
- 旧版后端目录
- 仅含 `.venv` 虚拟环境和 `__pycache__` 字节码文件
- 无实际源代码，已清理
