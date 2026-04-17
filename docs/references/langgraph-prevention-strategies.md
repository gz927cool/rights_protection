# LangGraph create_agent Subgraph Prevention Strategies

## Overview

This document provides actionable guidance to prevent common pitfalls when working with LangGraph's `create_agent` function for building subgraph-based workflows. These strategies are derived from a production incident involving message history loss and step routing failures.

---

## 1. Best Practices for create_agent Subgraphs

### 1.1 Always Use `graph=Command.PARENT` for Navigation

**Problem**: Navigation tools (e.g., `proceed_to_next_step`, `go_to_step`) returning `Command(goto=...)` without `graph=Command.PARENT` route within the child subgraph instead of the parent graph.

**Correct Pattern**:
```python
@tool
def proceed_to_next_step(runtime: ToolRuntime, step_answers: Dict[str, Any] = {}) -> Command:
    """Navigate to next step in PARENT graph."""
    updates = {
        "step_data": {...},
        "current_step": target_step_num,
    }
    return Command(goto=next_step_name, update=updates, graph=Command.PARENT)
```

**Incorrect Pattern** (causes routing errors):
```python
@tool
def proceed_to_next_step(runtime: ToolRuntime, ...) -> Command:
    return Command(goto=next_step_name, update=updates)  # Missing graph=Command.PARENT
```

**Why**: Without `graph=Command.PARENT`, LangGraph interprets the `goto` target as a node within the current subgraph. If the target node doesn't exist in the subgraph, you get:
```
Task tools with path ('__pregel_push', 0, False) wrote to unknown channel branch:to:step3_common, ignoring it.
```

---

### 1.2 Use `messages_add` Reducer for Conversation History

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

---

### 1.3 Don't Rely on Parent State Access from Within Subgraph

**Problem**: Agent subgraphs created by `create_agent` have isolated state. Accessing `runtime.state` for parent-level fields may not reflect the actual parent state.

**Correct Pattern**:
```python
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

### 1.4 Properly Propagate Messages Through Wrapper Functions

**Problem**: When calling `agent.stream()` inside a wrapper node, messages may not propagate correctly to parent state.

**Correct Pattern**:
```python
def _step_node_wrapper(step_name: str):
    agent = _get_step_agent(step_name)

    def wrapper(state: ConsultationState) -> Command | Dict:
        messages_to_send = list(state.get("messages", []))

        try:
            collected_messages = []
            for chunk in agent.stream(
                {"messages": messages_to_send},
                config={"configurable": {"name": step_name}, "system_message": dynamic_prompt},
                stream_mode="updates"
            ):
                for node_name, node_output in chunk.items():
                    if isinstance(node_output, dict) and "messages" in node_output:
                        collected_messages.extend(node_output["messages"])
        except ParentCommand as e:
            return e.args[0]

        # Deduplicate and filter
        existing_ids = {msg.id for msg in messages_to_send if hasattr(msg, 'id')}
        new_messages = [msg for msg in collected_messages
                       if not hasattr(msg, 'id') or msg.id not in existing_ids]

        return {"messages": new_messages}

    return wrapper
```

**Key Points**:
- Build `messages_to_send` without mutating state
- Deduplicate messages by ID to prevent duplicates
- Handle `ParentCommand` exception to return navigation Commands

---

## 2. Testing Guidance

### 2.1 Test Message History Preservation

```python
def test_message_history_preservation():
    """
    Verify that messages accumulate across multiple interactions.
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

### 2.2 Test Step Transitions

```python
def test_step_transitions():
    """
    Verify that step routing works correctly with graph=Command.PARENT.
    """
    graph = get_consultation_graph()
    config = {"configurable": {"thread_id": "test-routing"}}

    # Start at step2_initial
    initial_state = graph.invoke(
        {"messages": [HumanMessage(content="欠薪")], "current_step": 2},
        config
    )

    # Verify current_step updated
    assert initial_state["current_step"] > 2, "Should have advanced to next step"
    assert initial_state.get("case_category") == "欠薪", "case_category should be extracted"
```

### 2.3 Test Navigation Tools with graph=Command.PARENT

```python
def test_navigation_tools_parent_routing():
    """
    Verify navigation tools route to correct parent graph nodes.
    """
    graph = get_consultation_graph()

    # Simulate tool call that would route to step3_common
    nav_command = proceed_to_next_step.invoke({
        "runtime": MockToolRuntime(state={
            "messages": [AIMessage(content="", name="step2_initial")],
            "step_data": {},
        }),
        "step_answers": {"case_category": "欠薪"}
    })

    # Verify Command has graph=Command.PARENT
    assert isinstance(nav_command, Command)
    assert nav_command.graph == Command.PARENT
    assert nav_command.goto == "step3_common"
```

### 2.4 Integration Test Template

```python
def test_full_step_flow():
    """
    Full integration test for step2 -> step3 transition.
    """
    graph = get_consultation_graph()
    config = {"configurable": {"thread_id": "test-full-flow"}}

    # Step 2: Problem identification
    state = graph.invoke({
        "messages": [HumanMessage(content="被公司开除了，没有提前通知")],
        "current_step": 2,
    }, config)

    # Verify case_category extracted
    assert state.get("case_category") == "开除"

    # Verify step completed
    completed = state.get("completed_steps", set())
    assert 2 in completed, "step2 should be marked completed"

    # Verify now in step3
    assert state["current_step"] == 3, "Should be at step3_common"

    # Step 3: Collect general info
    state = graph.invoke({
        "messages": [HumanMessage(content="在职状态，已经签了合同")],
    }, config)

    # Verify step3_common processed without repeating questions
    # (agent should not ask about case_category again)
```

---

## 3. Code Review Checklist

### 3.1 Navigation Tools

- [ ] All navigation tools return `Command` with `graph=Command.PARENT`
- [ ] `proceed_to_next_step` correctly calculates target step
- [ ] `back_to_previous_step` marks dirty steps correctly
- [ ] `go_to_step` handles dirty range properly

```python
# Verify each navigation tool has graph=Command.PARENT
@tool
def my_navigation_tool(...) -> Command:
    return Command(goto=target, update=updates, graph=Command.PARENT)  # Required
```

### 3.2 Message State Definition

- [ ] `messages` uses `messages_add` reducer, not `_replace_list`
- [ ] `ConsultationState` and `ConsultationInput` both use correct reducers
- [ ] Other list fields (e.g., `evidence_items`) use appropriate reducers

```python
# Check consultation_state.py
class ConsultationState(TypedDict):
    messages: Annotated[List[Any], messages_add]  # Not _replace_list
    evidence_items: Annotated[List[EvidenceItem], _replace_list]  # OK for evidence
```

### 3.3 Wrapper Function

- [ ] Wrapper builds message list without mutating state
- [ ] Wrapper handles `ParentCommand` exception
- [ ] Wrapper deduplicates messages by ID
- [ ] Wrapper returns `{"messages": new_messages}` or the Command

### 3.4 Subgraph Isolation

- [ ] No direct access to parent `runtime.state["current_step"]` from within tools
- [ ] Step name extracted from `AIMessage.name` attribute
- [ ] Fallback logic for step name detection

```python
# Check tools don't rely on parent state
def proceed_to_next_step(runtime: ToolRuntime, ...):
    # Don't do this (unreliable in subgraph):
    current_step = runtime.state.get("current_step")

    # Do this instead:
    messages = runtime.state.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, 'name') and msg.name in STEP_NAMES:
            current_step_name = msg.name
            break
```

### 3.5 Reducer Functions

- [ ] `_replace_list` only used for replace-once fields (evidence, documents)
- [ ] `messages_add` used for all accumulated message history
- [ ] Custom reducers documented with clear purpose

---

## 4. Anti-Patterns to Avoid

### Anti-Pattern 1: Missing graph=Command.PARENT
```python
# WRONG
return Command(goto=next_step, update=updates)

# RIGHT
return Command(goto=next_step, update=updates, graph=Command.PARENT)
```

### Anti-Pattern 2: Mutating State Directly
```python
# WRONG - don't mutate state directly
state["messages"].append(new_message)
return state

# RIGHT - return updates
return {"messages": [new_message]}
```

### Anti-Pattern 3: Wrong Message Reducer for History
```python
# WRONG
messages: Annotated[List, _replace_list]

# RIGHT
messages: Annotated[List, messages_add]
```

### Anti-Pattern 4: Relying on Parent State in Subgraph
```python
# WRONG - parent state not accessible in subgraph
current_step = runtime.state["current_step"]

# RIGHT - extract from messages
for msg in reversed(runtime.state["messages"]):
    if msg.name in STEP_NAMES:
        current_step = STEP_NAMES.index(msg.name) + 2
        break
```

### Anti-Pattern 5: No Deduplication in Wrapper
```python
# WRONG - may return duplicate messages
return {"messages": collected_messages}

# RIGHT - filter out existing messages
existing_ids = {m.id for m in messages_to_send if hasattr(m, 'id')}
new_messages = [m for m in collected_messages if m.id not in existing_ids]
return {"messages": new_messages}
```

---

## 5. Quick Reference

| Pattern | Correct | Incorrect |
|---------|---------|------------|
| Navigation Command | `Command(goto=X, graph=Command.PARENT)` | `Command(goto=X)` |
| Message History | `messages_add` reducer | `_replace_list` reducer |
| Step Detection | From `AIMessage.name` | From `runtime.state["current_step"]` |
| Message Propagation | Return `{"messages": [...]}` | Mutate `state["messages"]` |
| Command from Exception | `return e.args[0]` | `return None` |

---

## Related Documentation

- [Message History and Routing Fix](../solutions/message-history-and-routing-fix.md)
- [LangGraph create_agent Refactor](./langgraph-create-agent-refactor.md)
- [Multi-Agent Handoffs Pattern](./multi-agent.md)
