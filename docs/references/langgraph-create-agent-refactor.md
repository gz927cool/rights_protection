---
title: "LangGraph Consultation Graph: 使用 create_agent 子图替代 model.bind_tools()"
problem_type: "architecture-refactor"
component: "langgraph_model/consultation_graph.py"
date: "2026-04-17"
tags:
  - "langchain"
  - "langgraph"
  - "create_agent"
  - "subgraph"
  - "agent-naming"
  - "handoffs"
  - "refactor"
related_components:
  - "langgraph_model/consultation_graph.py"
  - "docs/references/multi-agent.md"
  - "legacy/langgraph_model/legal_supervisor.py"
---

# LangGraph Agent 命名重构：model.bind_tools() → create_agent 子图

## 问题描述

需要为九步咨询系统的每个阶段设置智能体名称。使用 LangChain v1+ 的 `create_agent` 工厂函数，通过 `name` 参数标识每个智能体。

**目标**：将原来的 `model.bind_tools()` + 单一 node 函数模式，迁移到 `create_agent(..., name=step_name)` 子图模式。

## 根因分析

LangGraph 的 `create_agent` 创建的子图作为节点添加时，工具返回 `Command(goto=..., graph=Command.PARENT)` 必须满足：

1. `Command.update` 中必须包含 `ToolMessage` — 否则 LangGraph 抛出错误：
   ```
   Expected to have a matching ToolMessage in Command.update for tool 'proceed_to_next_step', got: []
   ```

2. `create_agent` 的 `name` 参数设置的是 `AIMessage.name` 字段，不是图节点名称（图节点名由 `add_node` 决定）

3. `system_message` 需通过 `agent.invoke(config={"system_message": ...})` 传入，而非构造函数 — 这样才能实现动态 prompt

## 解决方案

### 1. 导入

```python
from langchain.agents import create_agent
```

### 2. Agent 子图缓存

```python
_step_agents: Dict[str, Any] = {}

def _get_step_agent(step_name: str):
    """获取或创建指定步骤的 agent 子图（带 name 标识）"""
    if step_name in _step_agents:
        return _step_agents[step_name]

    tools = STEP_TOOL_SETS.get(step_name, STEP_TOOL_SETS["step2_initial"])
    system_prompt = build_step_system_prompt(step_name, {})

    agent = create_agent(
        model,
        tools=tools,
        system_prompt=system_prompt,
        name=step_name,  # Agent 级别名称标识
    )
    _step_agents[step_name] = agent
    return agent
```

### 3. 节点包装器（动态 System Prompt）

```python
def _step_node_wrapper(step_name: str):
    """
    包装函数：调用 create_agent 子图。
    - 动态 system prompt 通过 agent.invoke() 的 config 传入
    - 工具返回 Command(goto=..., graph=Command.PARENT) 由 LangGraph 自动处理路由
    """
    agent = _get_step_agent(step_name)

    def wrapper(state: ConsultationState) -> Command | Dict:
        # 交互模式：检查是否从 interrupt 恢复
        resume_input = state.get("__resume_input__")
        if resume_input:
            state["messages"].append(HumanMessage(content=resume_input, type="human"))
            state.pop("__resume_input__", None)

        # 动态 system prompt
        dynamic_prompt = build_step_system_prompt(step_name, state)

        # 调用 agent 子图
        result = agent.invoke(
            {"messages": state.get("messages", [])},
            config={
                "configurable": {"name": step_name},
                "system_message": dynamic_prompt,
            },
        )

        # agent.invoke() 返回 dict，直接返回
        return result

    return wrapper
```

### 4. 导航工具返回 Command + ToolMessage

```python
# proceed_to_next_step
tool_msg = ToolMessage(
    content=f"已推进到下一步: {next_step_name}",
    tool_call_id=runtime.tool_call_id,
)
_updates = dict(updates)
_updates["messages"] = [tool_msg]
return Command(goto=next_step_name, update=_updates)

# back_to_previous_step
tool_msg = ToolMessage(
    content=f"返回步骤: {step_name}",
    tool_call_id=runtime.tool_call_id,
)
_updates = dict(updates)
_updates["messages"] = [tool_msg]
return Command(goto=step_name, update=_updates)
```

### 5. 图构建器

```python
def create_consultation_graph():
    """
    架构（Agentic Handoffs 模式）：
    - 每个步骤是一个 create_agent 子图，带 name 参数标识
    - 导航工具返回 Command(goto=..., graph=Command.PARENT) 控制父图路由
    """
    workflow = StateGraph(
        ConsultationState,
        input_schema=ConsultationInput,
    )

    # 添加所有步骤节点（使用 create_agent 子图）
    for step_name in STEP_NAMES:
        workflow.add_node(step_name, _step_node_wrapper(step_name))

    # 条件边...
```

## 验证结果

| 测试 | 结果 |
|------|------|
| Graph 编译成功 | ✅ 10 个节点正确注册 |
| Step 1 输入"欠薪" | ✅ `Name: step2_initial` 正确显示 agent 名称 |
| Step 2 选择"B" | ✅ 跳转 `step3_common`，`current_step: 3` |

## 预防策略

### Command.update 必须包含 ToolMessage

导航工具返回 `Command` 时，`update["messages"]` 必须包含对应的 `ToolMessage`：

```python
tool_msg = ToolMessage(content="...", tool_call_id=runtime.tool_call_id)
_updates = dict(updates)
_updates["messages"] = [tool_msg]
return Command(goto=next_step, update=_updates)
```

### system_message 通过 config 传入

`system_message` 放在 `agent.invoke(config={...})` 中，而非 `create_agent()` 构造函数 — 这样才能实现动态注入：

```python
# ✅ 正确：动态传入
result = agent.invoke({"messages": ...}, config={"system_message": dynamic_prompt})

# ❌ 错误：构造函数中静态设置
agent = create_agent(model, ..., system_prompt=static_prompt)  # 无法动态修改
```

### agent.name 与图节点名是独立的

- `workflow.add_node(node_name, ...)` — 设置图节点名
- `create_agent(..., name=step_name)` — 设置 `AIMessage.name` 字段（用于追踪和标识）

### 节点包装器返回 dict，工具返回 Command

- `agent.invoke()` 返回字典（包含更新的 messages）
- 导航工具应返回 `Command(goto=..., update={...})`

## 相关文档

- [Multi-Agent Handoffs 模式](../references/multi-agent.md) — LangGraph 官方多智能体模式参考
- [Legacy Supervisor 实现](../../legacy/langgraph_model/legal_supervisor.py) — 旧的 `create_agent` 使用方式（已废弃）

## 关键要点

1. **ToolMessage 是必须的** — 任何返回 `Command` 的导航工具，都必须在 `update["messages"]` 中包含 `ToolMessage`
2. **动态 prompt 通过 config** — `system_message` 放在 `invoke` 的 config 中，而非构造函数
3. **直接添加子图** — `add_node(name, agent_subgraph)` 直接添加，LangGraph 自动处理 `Command.PARENT` 路由
4. **Agent 名称用于标识** — `name` 参数设置 AI 消息的 `.name` 字段，不影响图结构
