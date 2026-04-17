---
title: "Message History Loss and Step Routing Fix"
date: "2026-04-17"
status: "resolved"
tags:
  - "langgraph"
  - "create_agent"
  - "handoffs"
  - "message-history"
  - "command-routing"
related:
  - "docs/references/langgraph-create-agent-refactor.md"
---

# Message History Loss and Step Routing Fix

## Problem Summary

User reported two critical issues in the consultation graph:

1. **Message History Loss**: Agent couldn't access previous conversation history, causing repeated questions
2. **Step Routing Failure**: `proceed_to_next_step` tool didn't transition from step2_initial to step3_common

Error message:
```
Task tools with path ('__pregel_push', 0, False) wrote to unknown channel branch:to:step3_common, ignoring it.
```

## Root Causes

### Issue 1: Message History Loss

**Location**: `langgraph_model/consultation_graph.py:984-1009` (`_step_node_wrapper`)

**Problem**:
- The wrapper passed messages to agent subgraph but didn't properly propagate updated messages back to parent state
- Used `_replace_list` reducer which replaced messages instead of accumulating them
- State mutation (`state["messages"].append()`) didn't trigger checkpoint updates

**Impact**: Each step started with empty or incomplete message history, causing agents to repeat questions.

### Issue 2: Command Routing Failure

**Location**: Navigation tools (`proceed_to_next_step`, `back_to_previous_step`, `go_to_step`)

**Problem**:
- Tools returned `Command(goto=next_step)` without `graph=Command.PARENT` parameter
- Commands defaulted to routing within the child agent subgraph, not the parent graph
- Child subgraph had no `step3_common` node, causing routing error

**Impact**: Graph stayed in step2_initial instead of transitioning to step3_common.

## Solutions Implemented

### Fix 1: Message History Preservation

**Changed**: `consultation_state.py:216, 250`
```python
# Before
messages: Annotated[List[Any], _replace_list]

# After
messages: Annotated[List[Any], messages_add]
```

**Changed**: `consultation_graph.py:_step_node_wrapper`
```python
def wrapper(state: ConsultationState) -> Command | Dict:
    # Build message list without mutating state
    messages_to_send = list(state.get("messages", []))

    resume_input = state.get("__resume_input__")
    if resume_input:
        messages_to_send.append(HumanMessage(content=resume_input, type="human"))

    dynamic_prompt = build_step_system_prompt(step_name, state)

    # Use stream() to collect messages incrementally
    try:
        collected_messages = []
        for chunk in agent.stream(
            {"messages": messages_to_send},
            config={
                "configurable": {"name": step_name},
                "system_message": dynamic_prompt,
            },
        ):
            if "messages" in chunk:
                for msg in chunk["messages"]:
                    # Deduplicate by message ID
                    if not any(getattr(m, "id", None) == getattr(msg, "id", None)
                              for m in collected_messages):
                        collected_messages.append(msg)

        return {"messages": collected_messages}
    except ParentCommand as e:
        # Extract Command from exception
        return e.args[0]
```

### Fix 2: Command Routing with graph=Command.PARENT

**Changed**: All navigation tools

```python
# proceed_to_next_step (line 539)
return Command(goto=next_step_name, update=_updates, graph=Command.PARENT)

# back_to_previous_step (line 568)
return Command(goto=step_name, update=_updates, graph=Command.PARENT)

# go_to_step (line 457)
return Command(goto=step_name, update=updates, graph=Command.PARENT)
```

### Fix 3: Step Number Alignment

**Problem**: Agent subgraph doesn't have access to parent state, causing incorrect step number calculation.

**Solution**: Extract current step from AIMessage.name attribute instead of runtime.state:

```python
# proceed_to_next_step (lines 461-490)
# Extract step name from AIMessage.name (set by create_agent)
current_step_name = None
messages = runtime.messages or []
for msg in reversed(messages):
    if hasattr(msg, "name") and msg.name in STEP_NAMES:
        current_step_name = msg.name
        break

if not current_step_name:
    current_step_name = "step2_initial"

current_step_num = STEP_NAMES.index(current_step_name) + 2  # step2_initial=2
target_step_num = current_step_num + 2
```

## Verification

Test script: `test_step2_to_step3_flow.py`

**Test Scenario**:
1. Start with step2_initial
2. Agent asks: "请问您遇到了什么类型的劳动争议？"
3. User responds: "欠薪"
4. Verify transition to step3_common with case_category="欠薪"
5. User responds: "签了"
6. Verify no repeated questions

**Results**: ✅ ALL CHECKS PASSED

```
✅ Extracts case_category from user input
✅ Calls proceed_to_next_step with correct step_answers
✅ Transitions from step2_initial to step3_common
✅ Preserves message history across steps
✅ Prevents question repetition
✅ Allows step3_common agent to see previous conversation
```

## Key Learnings

### 1. Command.PARENT is Required for Subgraph Navigation

When a tool inside a `create_agent` subgraph needs to route the parent graph:
```python
return Command(goto=target_node, update={...}, graph=Command.PARENT)
```

Without `graph=Command.PARENT`, the Command tries to route within the child subgraph.

### 2. Message Accumulation vs Replacement

Use `messages_add` reducer for conversation history:
```python
messages: Annotated[List[Any], messages_add]  # Accumulates
```

Not `_replace_list`:
```python
messages: Annotated[List[Any], _replace_list]  # Replaces
```

### 3. Subgraph State Isolation

Agent subgraphs created by `create_agent` have isolated state. They cannot access parent state via `runtime.state`. Instead:
- Extract context from messages (e.g., AIMessage.name)
- Pass necessary data through tool parameters
- Use Command.update to propagate changes to parent

### 4. Message Deduplication

When using `agent.stream()`, deduplicate messages by ID to prevent duplicates:
```python
if not any(getattr(m, "id", None) == getattr(msg, "id", None)
          for m in collected_messages):
    collected_messages.append(msg)
```

### 5. ParentCommand Exception Handling

When tools return `Command(graph=Command.PARENT)`, LangGraph raises `ParentCommand` exception. Catch it and return the Command:
```python
try:
    result = agent.stream(...)
    return {"messages": collected_messages}
except ParentCommand as e:
    return e.args[0]  # Extract Command
```

## Related Documentation

- [LangGraph create_agent Refactor](../references/langgraph-create-agent-refactor.md)
- [Multi-Agent Handoffs Pattern](../references/multi-agent.md)
- [Frontend Message Display Issues](../debugging/frontend-message-display-issues-root-cause-analysis.md)

## Files Modified

- `langgraph_model/consultation_graph.py` - Fixed wrapper, added graph=Command.PARENT, fixed step numbering
- `langgraph_model/consultation_state.py` - Changed message reducer to messages_add
- `test_step2_to_step3_flow.py` - Created comprehensive test

## Status

✅ **RESOLVED** - All tests passing, message history preserved, routing works correctly.
