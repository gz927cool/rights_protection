# LLM 应用开发注意事项

> 本文档总结自本项目劳动争议智能咨询系统的实际开发经验，所有条目均来源于实际 bug 修复、返工和教训。

---

## 一、LangGraph 状态机开发

### 1.1 Command.PARENT 必须显式指定
子图内的导航工具返回 `Command` 时，**必须指定 `graph=Command.PARENT`**，否则路由只在子图内进行，父图无法识别目标节点。

```python
# 正确
return Command(goto=next_step_name, update=updates, graph=Command.PARENT)
# 错误：缺少 graph=Command.PARENT
return Command(goto=next_step_name, update=updates)
```

### 1.2 导航跳转时必须更新所有相关状态字段
状态机在执行导航跳转时，必须同时更新所有受该跳转影响的状态字段。只更新部分字段会导致状态不一致，流程停滞或路由破坏。

```python
updates = {
    "active_agent": next_step_name,  # 一个字段
    "current_step": target_step_num + 1,  # 另一个字段 —— 两个都要更新
}
```

### 1.3 子图返回必须与父状态合并
`create_agent` 子图只返回消息更新，直接返回会丢失父状态字段。

```python
# 正确：合并
response = agent.invoke(state)
return {**state, **response}
# 错误：直接返回
return response
```

### 1.4 消息历史使用 messages_add 而非 _replace_list
`_replace_list` 会替换整个历史而非追加，导致消息丢失。

```python
from operator import add as messages_add
messages: Annotated[List[Any], messages_add]  # 累积
messages: Annotated[List[Any], _replace_list]  # 替换（仅适用于 evidence 等字段）
```

### 1.5 子图内无法直接访问父状态
`runtime.state` 在 `create_agent` 子图内是隔离的，无法直接读取父图状态。

### 1.6 新会话判断要用 `not existing.values`
新会话 `graph.get_state()` 返回 `values={}`（空字典）而非 `None`。

```python
if existing is None or not existing.values:
    state = create_initial_state(...)
```

### 1.7 API 兼容性使用 hasattr
新版 LangGraph 的 `StateSnapshot` 没有 `.configurable` 属性。

```python
if hasattr(state, "configurable"):
    current_step = state.configurable.get("current_step", 1)
else:
    vals = dict(state.values) if hasattr(state, "values") else {}
    current_step = vals.get("current_step", 1)
```

### 1.8 流式输出的消息类型过滤策略由前端渲染方案决定
如果前端通过标记文本（如 `[TOOL_CALL:xxx]`）自行渲染交互组件，则应过滤 `system`/`human`/`tool` 类型避免重复渲染。如果前端需要直接展示工具调用状态（如"正在调用 xxx 工具"），则应将 `tool` 类型消息也发送给前端。关键是**前后端约定一致**，且任何场景下都不要发送 `system` 提示词内容。

```python
# 场景A：前端用标记渲染交互组件，只发 AI 消息
if msg_type not in ("system", "SystemMessage", "human", "tool"):
    yield f"event: content\ndata: {...}\n\n"

# 场景B：前端需要展示工具调用状态，发 AI + tool
if msg_type not in ("system", "SystemMessage", "human"):
    yield f"event: content\ndata: {...}\n\n"
```

---

## 二、SSE 流式接口开发

### 2.1 不要修改消息内容的换行符
SSE 协议本身用 `\n\n` 分隔事件，不需要对 content 做换行替换。JSON 编码会正确转义 `\n`。

```python
# 错误：破坏多行消息格式
content = msg.content.replace("\n", " ").replace("\r", "")

# 正确：直接 json.dumps
json.dumps({"content": msg.content, "done": False})
```

### 2.2 LLM 超时需要根据模型推理速度调整
默认超时（通常 30s）对于快速模型足够，但对复杂推理或慢速模型会导致 premature timeout。应通过实际测试确定适合的值，记录在配置中而非硬编码。

```python
# 错误：硬编码一个可能不适用的超时
q.get(timeout=30)

# 正确：从配置读取，典型值为 60-180s
q.get(timeout=settings.LLM_CHUNK_TIMEOUT)
```

---

## 三、前端消息处理

### 3.1 Session ID 必须使用真实 UUID
禁止使用占位符字符串（如 `"new"`）作为 session_id，所有新窗口会共享同一个标识。

```typescript
// 生成浏览器兼容的 UUID v4
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}
```

### 3.2 流式状态和消息状态分离
用独立的 `streamingContent` 追踪流式内容，避免频繁更新 messages 数组导致 race condition。

```typescript
const [streamingContent, setStreamingContent] = useState("")
// 流式过程中只更新 streamingContent，只有流结束时才更新 messages
```

### 3.3 错误必须有日志和 UI 显示
catch 块必须至少 `console.error` 记录错误，并通过 error state 渲染到 UI。

```typescript
catch (err) {
  console.error("解析流数据失败:", err)
  setError(err instanceof Error ? err.message : "网络连接失败")
}
```

### 3.4 SSE 解析器不能静默失败
空的 `catch {}` 会吞掉所有错误，让调试变成噩梦。

---

## 四、AI 交互模式

### 4.1 禁止规则比描述性规则更有效
AI 倾向于"生成内容"而非"遵守约束"，禁止规则比正向描述更能约束行为。

```python
# 有效：禁止规则
"禁止直接输出交互组件标记"
"流式对话中禁止出现阻塞性等待回复（如'请稍等'、'让我想想'），必须持续推进或等待用户输入"
```

### 4.2 交互工具必须防止 LLM 替用户做选择
LLM 可能直接输出交互组件的标记文本（如 `[SELECT_OPTION]`）代替用户选择。

修复方案：交互工具返回结构化 Dict，包含 `type: "awaiting_user_input"`，并在 prompt 中明确禁止直接输出任何交互标记。

### 4.3 AI 不擅长自检——必须测试驱动
AI 生成的内容需要通过实际运行来验证，不要依赖 AI 自我判断。

### 4.4 AI 被动的——不会主动联想
修改 A 文件时，AI 不会主动更新引用 A 的 B 文件，必须人工明确指出关联。

### 4.5 边界条件需要开发者主动触发
AI 更关注正常路径，不要等 AI 自己想到，要明确问"如果这个值为空会怎样"。

### 4.6 外部环境问题 AI 无法自愈
网络、API、第三方服务异常时，AI 反复重试但不会想到检查环境配置，需要人工介入。

---

## 五、架构设计原则

### 5.1 平衡自由度与可控性
- 完全依赖大模型：灵活但输出不可控，容易"一本正经胡说八道"
- 完全硬编码工作流：稳定但缺乏灵活性
- **推荐**："约束下的自主推理"——通过工作流配置定义职责边界，通过提示词工程设定专业思维框架

### 5.2 多角色协作架构（Supervisor Architecture）
- 协调者（Supervisor）统一接收问题，根据状态决定由哪个专业角色处理
- 专业角色专注自己领域，执行完毕后结果返回协调者
- 协调者具备"智能路由"能力

### 5.3 状态机设计的反模式
- **错误**：`while True` 循环 + `self-loop` 条件边（永远返回当前节点）
- **正确**：单次 LLM 调用 + `Command` 跳转，移除循环

### 5.4 增量修改优于批量重写
每次只让 AI 处理一种类型的变更，发现问题可快速定位和回滚。

### 5.5 涉及 LLM 应用的开发——让 AI 读文档而非凭记忆
LangGraph、Streaming 等库的 API 细节更新频繁，AI 的训练记忆容易过时。主动让 AI 去读官方文档获取准确信息。

---

## 六、典型问题模式速查

以下问题模式在本项目中实际出现过，其根因和干预方案已验证。

| 问题模式 | AI/系统表现 | 根因 | 有效干预 |
|---------|---------|------|---------|
| 工具循环调用 | 反复调用同一工具不推进 | 缺乏禁止规则或退出条件 | 添加明确的禁止规则和退出边界 |
| 状态不一致 | 步骤计数器停滞或跳转混乱 | 状态更新不完整（漏字段/子图状态未合并） | 导航跳转时更新所有受影响字段；子图返回时与父状态合并 |
| 流式消息重复/丢失 | 消息重复渲染或最终结果缺失 | 消息类型过滤策略与前端渲染方案不一致 | 前后端约定一致的过滤策略；使用 streaming state 隔离渲染状态 |
| 假死/无限等待 | AI 既不输出也不调用工具 | prompt 缺少强制性推进约束 | 添加禁止阻塞性回复的规则 |
| 边界值处理缺失 | 正常流程正确但异常输入崩溃 | 输入验证未覆盖边界 | 开发者主动提出边界场景并验证 |
| 外部依赖失败 | AI 反复重试同一操作 | 环境问题 AI 无法自愈 | 开发者介入检查网络/端口/权限 |
| API 版本不兼容 | 运行时属性访问报错 | 新版本库移除了某些属性 | 使用 `hasattr` 做防御性访问 |

---

## 七、项目相关文档

- `docs/references/langgraph-prevention-strategies.md` — 12 种反模式与预防策略
- `docs/solutions/integration-issues/langgraph-streaming-state-management-bugs.md` — 流式状态管理 Bug 修复
- `docs/references/langgraph-create-agent-refactor.md` — create_agent 子图重构指南
- `frontend-message-display-issues-*.md` (wiki) — 前端消息处理详细分析

---

## 八、核心结论

1. **人工审核要快**：AI 生成代码后立即审核，发现问题立刻反馈，修复成本最低
2. **环境问题及时介入**：当 AI 反复重试同一操作并持续失败时，检查网络、端口、权限等环境配置
3. **LLM 应用层开发让 AI 读文档**：prompt 和代码交织在一起，且库 API 更新频繁，训练记忆容易过时
4. **开发者是测试执行者，AI 是修复执行者**：不依赖 AI 自我判断，通过实际运行验证是否符合预期
