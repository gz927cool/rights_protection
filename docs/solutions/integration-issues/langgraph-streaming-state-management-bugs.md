---
title: "LangGraph 流式接口状态管理修复"
category: integration-issues
date: 2026/04/18
tags: [langgraph, streaming, state-management, create-agent-subgraph, v2-format]
related_issues: []
related_docs:
  - "docs/solutions/integration-issues/langgraph-subgraph-message-routing-fix.md"
  - "docs/references/langgraph-prevention-strategies.md"
---

## 问题描述

LangGraph 流式接口 `/chat/stream` 返回系统提示词给前端，同时 Agent 状态在多次调用中丢失，导致 `current_step` 和 `active_agent` 无法正确更新。

## 症状

1. **流式接口返回系统提示词** - 1585 字符的 `## 系统信息\n你是宿迁市总工会...` 被发送到前端
2. **current_step 固定为 0** - API 返回 `STEP_NAMES[0-1]` 导致显示乱码
3. **会话状态不更新** - 多次调用后 `active_agent` 仍为初始值
4. **新会话使用空状态** - `graph.get_state()` 返回 `values={}` 而非 `None`

## 根因分析

### 1. 流式消息未过滤

`stream_mode="messages" + version="v2"` 返回的 chunks 结构为：
```python
{"type": "messages", "ns": (), "data": (message_chunk, metadata)}
```

其中 `message_chunk` 可能是 `system`、`human`、`tool` 或 `ai` 类型。原代码只过滤了 `system`，未过滤 `human` 和 `tool` 消息。

### 2. _step_node_wrapper 返回值不完整

`create_agent` 子图只返回 `{"messages": [...]}`，未合并父状态。wrapper 原代码：
```python
response = agent.invoke(state)
return response  # 丢失 active_agent, current_step 等字段
```

### 3. proceed_to_next_step 只更新一个字段

工具只更新了 `active_agent`（步骤名），未更新 `current_step`（步骤编号）：
```python
updates = {
    "active_agent": next_step_name,  # 有
    "current_step": ???,             # 缺失
}
```

### 4. 新会话判断条件错误

```python
existing = graph.get_state(config)
if existing is None:  # existing.values 是 {} 不是 None
    state = create_initial_state(...)
```

### 5. StateSnapshot API 差异

新版本 `StateSnapshot` 没有 `.configurable` 属性，只有 `.values`。

## 解决方案

### 1. 流式消息过滤 (main.py)

```python
# Handle content - skip system, human, and tool messages
if hasattr(msg_chunk, "content") and msg_chunk.content:
    msg_type = getattr(msg_chunk, "type", None) or getattr(msg_chunk, "name", "ai")
    if msg_type not in ("system", "SystemMessage", "human", "tool"):
        content_payload = _json.dumps({
            "content": msg_chunk.content,
            "role": "assistant",
        })
        yield f"event: content\ndata: {content_payload}\n\n"
```

### 2. _step_node_wrapper 状态合并 (consultation_graph.py)

```python
response = agent.invoke(state)
# Merge agent response with parent state - create_agent only returns messages
return {**state, **response}
```

### 3. proceed_to_next_step 同时更新两个字段 (consultation_graph.py)

```python
updates = {
    "active_agent": next_step_name,
    "current_step": target_step_num + 1,
    "messages": [last_ai_message, transfer_message],
}
```

### 4. 新会话判断条件 (main.py)

```python
if existing is None or not existing.values:
    state = create_initial_state(session_id, message.member_id)
```

### 5. get_session API 兼容性 (main.py)

```python
if hasattr(state, "configurable"):
    current_step = state.configurable.get("current_step", 1)
    completed = list(state.configurable.get("completed_steps", []))
    vals = state.values if hasattr(state, "values") else {}
else:
    vals = dict(state.values) if hasattr(state, "values") else {}
    current_step = vals.get("current_step", 1)
    completed = list(vals.get("completed_steps", []))
```

## 修改文件

- `main.py` - 流式接口过滤 + 状态初始化 + API 兼容性
- `langgraph_model/consultation_graph.py` - wrapper 状态合并 + 工具字段更新

## 预防策略

1. **create_agent 子图必须合并状态** - `{**state, **response}`
2. **导航工具更新所有相关字段** - active_agent + current_step
3. **新会话检查 `not existing.values`** - 空 dict {} 也是 falsy
4. **消息类型过滤** - 流式接口需过滤 system/human/tool
5. **API 兼容性检查** - 使用 `hasattr` 而非直接访问属性

## 相关文档

- [LangGraph 子图消息路由修复](docs/solutions/integration-issues/langgraph-subgraph-message-routing-fix.md)
- [LangGraph 预防策略参考](docs/references/langgraph-prevention-strategies.md)
