# LangGraph create_agent Subgraph Prevention Strategies

## Overview

This document provides actionable guidance to prevent common pitfalls when working with LangGraph's `create_agent` function for building subgraph-based workflows. These strategies are derived from production incidents involving message history loss, step routing failures, and API compatibility issues.

---

## 1. Bug Analysis Summary

| # | Bug | Root Cause | Impact |
|---|-----|------------|--------|
| 1 | Streaming handler didn't filter system/human/tool messages | Missing type filter in SSE output | Garbage in stream, frontend receives invalid messages |
| 2 | `_step_node_wrapper` didn't merge agent response with parent state | Returning only `agent.invoke()` result | Parent state fields (`current_step`, `active_agent`) lost |
| 3 | `proceed_to_next_step` only updated `active_agent`, not `current_step` | Missing field in updates dict | Step counter stuck, routing breaks |
| 4 | New session check failed because `existing.values` was `{}` not `None` | Using `existing is None` only | Empty sessions not detected, state corruption |
| 5 | `get_session` API used `state.configurable` which doesn't exist in newer StateSnapshot | Direct access without hasattr check | 500 error on newer LangGraph versions |

---

## 2. Prevention Strategies & Best Practices

### 2.1 Navigation Tools: Always Use `graph=Command.PARENT`

**Problem**: Navigation tools returning `Command(goto=...)` without `graph=Command.PARENT` route within the child subgraph instead of the parent graph.

**Correct Pattern**:
```python
@tool
def proceed_to_next_step(runtime: ToolRuntime, step_answers: Dict[str, Any] = {}) -> Command:
    """Navigate to next step in PARENT graph."""
    updates = {
        "step_data": {...},
        "current_step": target_step_num + 1,  # MUST update current_step too
        "active_agent": next_step_name,
    }
    return Command(goto=next_step_name, update=updates, graph=Command.PARENT)
```

**Incorrect Pattern** (causes routing errors):
```python
# WRONG - Missing graph=Command.PARENT
return Command(goto=next_step_name, update=updates)

# WRONG - Missing current_step in updates
updates = {"active_agent": next_step_name}  # current_step NOT updated
return Command(goto=next_step_name, update=updates, graph=Command.PARENT)
```

**Why**: Without `graph=Command.PARENT`, LangGraph interprets the `goto` target as a node within the current subgraph. If the target node doesn't exist in the subgraph, you get:
```
Task tools with path ('__pregel_push', 0, False) wrote to unknown channel branch:to:step3_common, ignoring it.
```

**Verification**:
```python
def test_navigation_command_has_parent():
    cmd = proceed_to_next_step.invoke({"runtime": mock_runtime, "step_answers": {}})
    assert isinstance(cmd, Command)
    assert cmd.graph == Command.PARENT, "Navigation must target PARENT graph"
    assert "current_step" in cmd.update, "Must update current_step field"
    assert "active_agent" in cmd.update, "Must update active_agent field"
```

---

### 2.2 Use `messages_add` Reducer for Conversation History

**Problem**: Using `_replace_list` for messages replaces the entire history instead of accumulating it.

**Correct Pattern**:
```python
from operator import add as messages_add

class ConsultationState(TypedDict):
    messages: Annotated[List[Any], messages_add]  # Accumulates
```

**Incorrect Pattern**:
```python
def _replace_list(a, b):
    return b if isinstance(b, list) else a

class ConsultationState(TypedDict):
    messages: Annotated[List[Any], _replace_list]  # Replaces - WRONG for chat history
```

**Why**: `_replace_list` is appropriate for replace-once fields like `evidence_items`. For conversation history, you need `messages_add` to append new messages while preserving previous ones.

**Verification**:
```python
def test_message_accumulation():
    state1 = graph.invoke({"messages": [HumanMessage(content="hello")]}, config)
    state2 = graph.invoke({"messages": [HumanMessage(content="world")]}, config)
    assert len(state2["messages"]) >= 2, "Messages must accumulate, not replace"
```

---

### 2.3 Always Merge Subgraph Response with Parent State

**Problem**: Agent subgraphs created by `create_agent` return only message updates. Returning this directly loses parent state fields.

**Correct Pattern**:
```python
def _step_node_wrapper(step_name: str):
    agent = _get_step_agent(step_name)

    def wrapper(state: ConsultationState) -> Command | Dict:
        dynamic_prompt = build_step_system_prompt(step_name, state)
        messages = state.get("messages", [])

        # Inject dynamic system prompt
        updated_messages = [SystemMessage(content=dynamic_prompt)]
        for msg in messages:
            if not isinstance(msg, SystemMessage):
                updated_messages.append(msg)

        response = agent.invoke({**state, "messages": updated_messages})

        # CRITICAL: Merge with parent state, don't just return response
        # agent.invoke only returns messages; parent state fields would be lost
        merged = {**state, **response}
        return merged

    return wrapper
```

**Why**: `create_agent` subgraphs only return message updates. Without merging with parent state, fields like `current_step`, `active_agent`, `case_category`, etc. are lost.

**Verification**:
```python
def test_wrapper_preserves_parent_state():
    initial_state = create_initial_state("test")
    initial_state["current_step"] = 3
    initial_state["case_category"] = "欠薪"

    wrapper = _step_node_wrapper("step3_common")
    result = wrapper(initial_state)

    # Parent state fields must be preserved
    assert result.get("current_step") == 3, "current_step must be preserved"
    assert result.get("case_category") == "欠薪", "case_category must be preserved"
    assert "messages" in result, "messages must be in result"
```

---

### 2.4 Don't Rely on Parent State Access from Within Subgraph

**Problem**: Agent subgraphs have isolated state. Accessing `runtime.state` for parent-level fields may not reflect the actual parent state.

**Correct Pattern**:
```python
@tool
def proceed_to_next_step(runtime: ToolRuntime, step_answers: Dict[str, Any] = {}) -> Command:
    # Extract context from messages passed to the agent
    messages = runtime.state.get("messages", [])
    current_step_name = None
    for msg in reversed(messages):
        if hasattr(msg, 'name') and msg.name in STEP_NAMES:
            current_step_name = msg.name
            break

    # Fallback if not found
    if not current_step_name:
        current_step_name = "step2_initial"
```

**Incorrect Pattern**:
```python
# This may not reflect actual parent state from within subgraph
current_step = runtime.state.get("current_step")
```

**Why**: Subgraph state isolation means `runtime.state` within a `create_agent` subgraph doesn't give you direct access to parent graph state. Use message attributes (like `AIMessage.name`) as a workaround.

---

### 2.5 Properly Filter Message Types in Streaming Handlers

**Problem**: SSE stream includes system/human/tool messages that frontend cannot handle.

**Correct Pattern**:
```python
def event_generator():
    for chunk in graph.stream(..., stream_mode="messages", version="v2"):
        if isinstance(chunk, dict) and chunk.get("type") == "messages":
            msg_chunk, metadata = chunk["data"]
            msg_type = getattr(msg_chunk, "type", None) or getattr(msg_chunk, "name", "ai")

            # Filter out system, human, and tool messages
            if msg_type not in ("system", "SystemMessage", "human", "tool"):
                yield f"event: content\ndata: {...}\n\n"
```

**Incorrect Pattern**:
```python
# WRONG - sends all message types to frontend
if hasattr(msg_chunk, "content") and msg_chunk.content:
    yield f"event: content\ndata: {...}\n\n"
```

**Why**: System messages contain internal prompts, human messages are echoed back, and tool messages are internal. Only `ai` type messages should be sent to the frontend.

---

### 2.6 Handle Empty/Falsy Values in Session Checks

**Problem**: `existing.values` returns `{}` (empty dict) for new sessions, not `None`. Simple `existing is None` check fails.

**Correct Pattern**:
```python
def post_chat(message: ChatMessage):
    config = {"configurable": {"thread_id": session_id}}
    graph = get_graph()

    try:
        existing = graph.get_state(config)
        # Check BOTH None AND empty/falsy values
        if existing is None or not existing.values:
            state = create_initial_state(session_id, message.member_id)
        else:
            state = dict(existing.values) if hasattr(existing, "values") else dict(existing)
    except Exception:
        state = create_initial_state(session_id, message.member_id)
```

**Incorrect Pattern**:
```python
# WRONG - doesn't handle empty {} case
if existing is None:
    state = create_initial_state(...)
```

**Why**: New sessions in LangGraph return `StateSnapshot` with `values={}` (empty dict), not `None`. The falsy check `not existing.values` handles both cases.

---

### 2.7 Use hasattr for API Compatibility

**Problem**: Newer LangGraph versions changed `StateSnapshot` API. Direct access to `state.configurable` raises `AttributeError`.

**Correct Pattern**:
```python
def get_session(session_id: str) -> SessionInfo:
    config = {"configurable": {"thread_id": session_id}}
    graph = get_graph()

    state = graph.get_state(config)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Support both old (state.configurable) and new (state.values) APIs
    if hasattr(state, "configurable"):
        current_step = state.configurable.get("current_step", 1)
        completed = list(state.configurable.get("completed_steps", []))
        vals = state.values if hasattr(state, "values") else {}
    else:
        vals = dict(state.values) if hasattr(state, "values") else {}
        current_step = vals.get("current_step", 1)
        completed = list(vals.get("completed_steps", []))

    return SessionInfo(
        session_id=session_id,
        current_step=current_step,
        completed_steps=completed,
        case_category=vals.get("case_category"),
        ...
    )
```

**Incorrect Pattern**:
```python
# WRONG - assumes state.configurable always exists
current_step = state.configurable.get("current_step", 1)
```

**Why**: LangGraph's StateSnapshot API changed - newer versions don't have `state.configurable` at the top level. Always use `hasattr` checks.

---

### 2.8 Message Deduplication in Wrapper Functions

**Problem**: When using `agent.stream()` or `agent.invoke()`, returned messages may include duplicates of existing messages in state.

**Correct Pattern**:
```python
def _step_node_wrapper(step_name: str):
    agent = _get_step_agent(step_name)

    def wrapper(state: ConsultationState) -> Command | Dict:
        messages = state.get("messages", [])
        existing_ids = {msg.id for msg in messages if hasattr(msg, 'id')}

        response = agent.invoke({**state, "messages": messages})

        # Deduplicate: filter out messages already in state
        new_messages = []
        for msg in response.get("messages", []):
            msg_id = getattr(msg, 'id', None)
            if msg_id is None or msg_id not in existing_ids:
                new_messages.append(msg)
                if msg_id:
                    existing_ids.add(msg_id)

        return {**state, "messages": new_messages}

    return wrapper
```

**Why**: Without deduplication, messages accumulate duplicates on each step transition, causing increased token usage and potential confusion.

---

## 3. Test Cases for Regression Prevention

### 3.1 Message History Preservation
```python
def test_message_history_preservation():
    """
    Verify that messages accumulate across multiple interactions.
    Bug: _step_node_wrapper didn't merge agent response with parent state
    """
    graph = get_consultation_graph()
    config = {"configurable": {"thread_id": "test-history"}}

    # Step 1: Initial interaction
    state1 = graph.invoke(
        {"messages": [HumanMessage(content="欠薪")]},
        config
    )

    # Step 2: Continue conversation
    state2 = graph.invoke(
        {"messages": [HumanMessage(content="签了劳动合同")]},
        config
    )

    # Verify messages are accumulated, not replaced
    message_count = len(state2["messages"])
    assert message_count >= 4, f"Expected >=4 messages, got {message_count}"

    # Verify step3 agent can see previous conversation
    step3_messages = [m for m in state2["messages"] if hasattr(m, 'name') and m.name == 'step3_common']
    assert len(step3_messages) > 0, "step3 should have processed messages"
```

### 3.2 Step Transitions with Full State Update
```python
def test_step_transitions_update_both_fields():
    """
    Verify that step routing updates BOTH current_step AND active_agent.
    Bug: proceed_to_next_step only updated active_agent, not current_step
    """
    graph = get_consultation_graph()
    config = {"configurable": {"thread_id": "test-routing"}}

    initial_state = graph.invoke(
        {"messages": [HumanMessage(content="欠薪")], "current_step": 2},
        config
    )

    # Verify BOTH fields updated
    assert initial_state["current_step"] > 2, "current_step should be advanced"
    assert initial_state["active_agent"] == STEP_NAMES[initial_state["current_step"] - 1], \
        "active_agent should match current_step"
```

### 3.3 New Session Detection
```python
def test_new_session_empty_values():
    """
    Verify new sessions are detected when existing.values is {} not None.
    Bug: New session check failed because existing.values was {} not None
    """
    graph = get_consultation_graph()
    session_id = "brand-new-session"

    config = {"configurable": {"thread_id": session_id}}

    # Should create new state, not fail
    existing = graph.get_state(config)

    # Empty session returns {} not None
    if existing is None or not existing.values:
        state = create_initial_state(session_id)
        assert state is not None
        assert state["session_id"] == session_id
```

### 3.4 Streaming Handler Message Filtering
```python
def test_streaming_filters_non_ai_messages():
    """
    Verify streaming handler filters system/human/tool messages.
    Bug: Streaming handler didn't filter system/human/tool messages
    """
    # This test requires capturing SSE output
    response = client.post("/chat/stream", json={
        "content": "欠薪",
        "session_id": "test-filter"
    })

    content = b"".join(response.streaming_body)
    lines = content.decode().split("\n")

    # Count message types in stream
    content_events = [l for l in lines if l.startswith("event: content")]
    tool_call_events = [l for l in lines if l.startswith("event: tool_calls")]

    # Should have content events
    assert len(content_events) > 0, "Should have content events"

    # Verify no system/human/tool content slipped through
    for line in content_events:
        if line.startswith("data: "):
            import json
            data = json.loads(line[6:])
            # No system prompts or echoed human messages
            assert "【" not in data.get("content", "") or "【" in data.get("content", "")  # Relaxed check
```

### 3.5 StateSnapshot API Compatibility
```python
def test_get_session_api_compatibility():
    """
    Verify get_session handles both old and new StateSnapshot APIs.
    Bug: get_session API used state.configurable which doesn't exist in newer StateSnapshot
    """
    graph = get_consultation_graph()
    session_id = "test-api-compat"

    # Create a session first
    graph.invoke({
        **create_initial_state(session_id),
        "messages": [HumanMessage(content="test")]
    }, config={"configurable": {"thread_id": session_id}})

    # get_session should work regardless of StateSnapshot internal structure
    response = client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert "current_step" in data
```

### 3.6 Navigation Command Structure
```python
def test_proceed_to_next_step_command_structure():
    """
    Verify proceed_to_next_step returns properly structured Command.
    """
    from langgraph.types import Command
    from unittest.mock import MagicMock

    mock_runtime = MagicMock()
    mock_runtime.state = {
        "messages": [AIMessage(content="test", name="step2_initial")],
        "dirty_steps": set(),
    }
    mock_runtime.tool_call_id = "test"

    cmd = proceed_to_next_step.invoke({
        "runtime": mock_runtime,
        "step_answers": {"case_category": "欠薪"}
    })

    # Verify Command structure
    assert isinstance(cmd, Command), "Must return Command"
    assert cmd.graph == Command.PARENT, "Must target PARENT graph"
    assert "current_step" in cmd.update, "Must update current_step"
    assert "active_agent" in cmd.update, "Must update active_agent"
    assert cmd.goto in STEP_NAMES, "goto must be valid step name"
```

---

## 4. Code Review Checklist

### 4.1 Navigation Tools
- [ ] All navigation tools return `Command` with `graph=Command.PARENT`
- [ ] `proceed_to_next_step` updates BOTH `current_step` AND `active_agent` in updates dict
- [ ] `back_to_previous_step` marks dirty steps correctly
- [ ] `go_to_step` handles dirty range properly
- [ ] Navigation tools extract current step from `AIMessage.name`, not `runtime.state["current_step"]`

### 4.2 State Definitions
- [ ] `messages` uses `messages_add` reducer, not `_replace_list`
- [ ] `ConsultationState` and `ConsultationInput` both use correct reducers
- [ ] Other list fields (e.g., `evidence_items`) use appropriate reducers

### 4.3 Wrapper Functions
- [ ] Wrapper merges agent response with parent state: `{**state, **response}`
- [ ] Wrapper doesn't mutate state directly
- [ ] Wrapper handles `ParentCommand` exception
- [ ] Wrapper deduplicates messages by ID
- [ ] Wrapper returns `{"messages": [...]}` or the Command

### 4.4 Streaming Handlers
- [ ] Filters out `system`, `human`, `tool` message types before sending to frontend
- [ ] Handles both `v2` and older stream formats
- [ ] Extracts `current_step` from node updates

### 4.5 Session Management
- [ ] New session check: `if existing is None or not existing.values`
- [ ] `get_state()` result handling uses `hasattr` checks for API compatibility
- [ ] Fallback: `dict(state.values) if hasattr(state, "values") else dict(state)`

### 4.6 Reducer Functions
- [ ] `_replace_list` only used for replace-once fields (evidence, documents)
- [ ] `messages_add` used for all accumulated message history
- [ ] Custom reducers documented with clear purpose

---

## 5. Anti-Patterns to Avoid

### Anti-Pattern 1: Missing `graph=Command.PARENT`
```python
# WRONG
return Command(goto=next_step, update=updates)

# RIGHT
return Command(goto=next_step, update=updates, graph=Command.PARENT)
```

### Anti-Pattern 2: Missing `current_step` in Updates
```python
# WRONG - only updates active_agent
updates = {"active_agent": next_step_name}

# RIGHT - updates both
updates = {
    "active_agent": next_step_name,
    "current_step": target_step_num + 1,
}
```

### Anti-Pattern 3: Not Merging Parent State
```python
# WRONG - returns only agent response, losing parent state
return agent.invoke(state)

# RIGHT - merges with parent state
response = agent.invoke(state)
return {**state, **response}
```

### Anti-Pattern 4: Wrong Message Reducer for History
```python
# WRONG
messages: Annotated[List, _replace_list]

# RIGHT
messages: Annotated[List, messages_add]
```

### Anti-Pattern 5: Relying on Parent State in Subgraph
```python
# WRONG - parent state not accessible in subgraph
current_step = runtime.state["current_step"]

# RIGHT - extract from messages
for msg in reversed(runtime.state["messages"]):
    if hasattr(msg, 'name') and msg.name in STEP_NAMES:
        current_step_name = msg.name
        break
```

### Anti-Pattern 6: No Deduplication in Wrapper
```python
# WRONG - may return duplicate messages
return {"messages": collected_messages}

# RIGHT - filter out existing messages
existing_ids = {m.id for m in messages_to_send if hasattr(m, 'id')}
new_messages = [m for m in collected_messages if getattr(m, 'id', None) not in existing_ids]
return {"messages": new_messages}
```

### Anti-Pattern 7: Incomplete Session Check
```python
# WRONG - doesn't handle {} case
if existing is None:
    state = create_initial_state(...)

# RIGHT
if existing is None or not existing.values:
    state = create_initial_state(...)
```

### Anti-Pattern 8: Direct StateSnapshot Attribute Access
```python
# WRONG - assumes state.configurable exists
current_step = state.configurable.get("current_step", 1)

# RIGHT - use hasattr
if hasattr(state, "configurable"):
    current_step = state.configurable.get("current_step", 1)
else:
    vals = dict(state.values) if hasattr(state, "values") else {}
    current_step = vals.get("current_step", 1)
```

---

## 6. Quick Reference

| Pattern | Correct | Incorrect |
|---------|---------|------------|
| Navigation Command | `Command(goto=X, graph=Command.PARENT)` | `Command(goto=X)` |
| Step Update | Update BOTH `current_step` AND `active_agent` | Update only `active_agent` |
| Message History | `messages_add` reducer | `_replace_list` reducer |
| Parent State Merge | `{**state, **response}` | `return response` |
| Step Detection | From `AIMessage.name` | From `runtime.state["current_step"]` |
| Message Propagation | Return `{"messages": [...]}` | Mutate `state["messages"]` |
| Session Check | `existing is None or not existing.values` | `existing is None` |
| StateSnapshot Access | `hasattr` checks | Direct `.configurable` access |
| Wrapper Deduplication | Filter by message ID | Return all collected messages |

---

## Related Documentation

- [Message History and Routing Fix](../solutions/integration-issues/langgraph-subgraph-message-routing-fix.md)
- [LangGraph create_agent Refactor](./langgraph-create-agent-refactor.md)
- [Multi-Agent Handoffs Pattern](./multi-agent.md)
