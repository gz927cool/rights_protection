---
title: "Session Isolation Bug - Multiple Browser Tabs Shared State"
category: ui-bugs
date: "2026-04-20"
tags:
  - session-management
  - frontend-backend-integration
  - browser-tabs
  - react-state
problem_type: ui-bugs
components:
  - frontend/ChatPage.tsx
  - backend/main.py
symptoms: |
  - Multiple browser tabs sharing same session state
  - New tab opening /chat immediately jumps to step 3 (same as existing session)
  - Session progress bleeding between tabs
---

## Problem Description

用户在第3步时，新打开的浏览器窗口访问 `/chat` URL 会立即继承旧窗口的会话状态（跳到第3步），而不是开始新的独立会话。

## Root Cause

前端 `ChatPage.tsx` 使用字符串 `"new"` 作为占位符 session_id：

```typescript
// Before (Bug)
const [activeSessionId, setActiveSessionId] = useState(sessionId || "new")
```

后端 `main.py` 的 session_id 处理逻辑：

```python
# main.py:211
session_id = message.session_id or str(uuid.uuid4())
```

**问题链**：
1. 所有新窗口都发送 `session_id: "new"` 给后端
2. `"new"` 是 truthy 字符串，不会触发 `uuid4()` 生成新 ID
3. 后端直接用 `"new"` 作为 `thread_id` 存储状态
4. 结果：所有新窗口共享同一个 thread_id = `"new"`

## Solution

### 1. 前端生成真实 UUID

```typescript
// Generate UUID v4 (browser-compatible)
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

// Use in useState
const [activeSessionId, setActiveSessionId] = useState(
  sessionId || generateUUID()
)
```

### 2. 移除占位符判断逻辑

```typescript
// Before
if (!activeSessionId || activeSessionId === "new") return

// After
if (!activeSessionId) return
```

```typescript
// Before
if (activeSessionId !== "new") { fetch(...) }

// After
if (activeSessionId) { fetch(...) }
```

## Architecture Principle

**session_id 应该由前端维护**：
- 前端：生成 UUID → 存储在 state → 每次请求传递
- 后端：接收并使用 session_id 作为 thread_id 存储/恢复状态
- 永远不要使用占位符字符串（如 `"new"`, `"default"`, `"temp"`）

## Prevention Strategies

### Code-Level Prevention

1. **Never use placeholder strings** as session identifiers
2. **Always validate session_id format** (UUID v4 regex)
3. **Frontend owns session lifecycle**: generate → store → pass → receive updates
4. **Backend validates but doesn't generate**: treat all input as potentially invalid

### Validation Helper (Recommended)

```typescript
function isValidUUID(id: string): boolean {
  const uuidV4Regex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
  return uuidV4Regex.test(id)
}

// Use in initialization
const [activeSessionId, setActiveSessionId] = useState(() => {
  if (sessionId && isValidUUID(sessionId)) {
    return sessionId
  }
  return generateUUID()
})
```

### Backend Validation (Recommended)

```python
import re

UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)

def is_valid_uuid(session_id: str) -> bool:
    if not session_id or not isinstance(session_id, str):
        return False
    return bool(UUID_PATTERN.match(session_id))
```

### Test Cases

```typescript
// Frontend unit test
test('rejects placeholder strings', () => {
  expect(isValidUUID('new')).toBe(false)
  expect(isValidUUID('')).toBe(false)
})

test('accepts valid UUIDs', () => {
  expect(isValidUUID(generateUUID())).toBe(true)
})
```

## Related Documentation

- [docs/solutions/integration-issues/langgraph-streaming-state-management-bugs.md](integration-issues/langgraph-streaming-state-management-bugs.md) - LangGraph session handling patterns
- [docs/references/langgraph-prevention-strategies.md](../references/langgraph-prevention-strategies.md) - Prevention strategies including session empty values check (Section 2.6)

## Files Changed

- `frontend/src/pages/ChatPage.tsx` - UUID generation, removed "new" placeholder
- `frontend/src/components/InfoPanel.tsx` - Step mapping fix (related issue)

## Commit

```
ff95a8f - fix: replace 'new' placeholder with proper UUID generation for session isolation
```
