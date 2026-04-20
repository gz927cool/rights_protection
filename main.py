"""
FastAPI 聊天接口 - 九步劳动争议咨询系统

提供类 ChatGPT 的流式聊天体验。
"""
import uuid
import os
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, AsyncIterator, List, Dict
from contextlib import asynccontextmanager
import anyio

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from langgraph.graph import START, END
from langgraph_model.consultation_graph import get_consultation_graph
from langgraph_model.consultation_state import (
    create_initial_state,
    STEP_DISPLAY_NAMES,
    STEP_NAMES,
)

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="劳动争议智能咨询系统",
    description="九步引导式劳动争议咨询，流式输出",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Lifespan
# ============================================================================

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = get_consultation_graph()
    return _graph


# ============================================================================
# Request / Response Models
# ============================================================================

class ChatMessage(BaseModel):
    content: str
    session_id: Optional[str] = None
    member_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    finish_reason: str
    current_step: int
    current_step_name: str
    done: bool


class SessionInfo(BaseModel):
    session_id: str
    current_step: int
    current_step_name: str
    completed_steps: list
    case_category: Optional[str] = None
    evidence_items: Optional[List[Dict]] = None
    qualification: Optional[Dict] = None
    document_draft: Optional[Dict] = None
    risk_assessment: Optional[Dict] = None


@app.get("/")
def root():
    return {
        "name": "劳动争议智能咨询系统",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/sessions/{session_id}")
def get_session(session_id: str) -> SessionInfo:
    """查询会话状态（含完整案件数据）"""
    config = {"configurable": {"thread_id": session_id}}
    graph = get_graph()

    try:
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
            current_step_name=STEP_DISPLAY_NAMES.get(
                STEP_NAMES[current_step - 1],
                STEP_NAMES[current_step - 1],
            ),
            completed_steps=completed,
            case_category=vals.get("case_category"),
            evidence_items=vals.get("evidence_items"),
            qualification=vals.get("qualification"),
            document_draft=vals.get("document_draft"),
            risk_assessment=vals.get("risk_assessment"),
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/chat")
def post_chat(message: ChatMessage):
    """
    非流式聊天接口（简单场景）
    """
    session_id = message.session_id or str(uuid.uuid4())

    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 100,
    }

    graph = get_graph()

    # 初始化或获取状态
    try:
        existing = graph.get_state(config)
        if existing is None or not existing.values:
            state = create_initial_state(session_id, message.member_id)
        else:
            state = dict(existing.values) if hasattr(existing, "values") else dict(existing)
    except Exception:
        state = create_initial_state(session_id, message.member_id)

    # 执行
    from langchain_core.messages import HumanMessage

    result = graph.invoke(
        {
            **state,
            "messages": [HumanMessage(content=message.content)],
        },
        config=config,
    )

    # 提取最后一条 AI 消息
    ai_message = ""
    finish_reason = "stop"
    for msg in reversed(result.get("messages", [])):
        msg_type = getattr(msg, "type", None) or getattr(msg, "name", "")
        if msg_type == "ai":
            ai_message = msg.content
            finish_reason = msg.response_metadata.get("finish_reason", "stop") if hasattr(msg, "response_metadata") else "stop"
            break

    current_step = result.get("current_step", 1)

    return {
        "session_id": session_id,
        "message": ai_message,
        "finish_reason": finish_reason,
        "current_step": current_step,
        "current_step_name": STEP_DISPLAY_NAMES.get(STEP_NAMES[current_step - 1], STEP_NAMES[current_step - 1]),
        "done": current_step >= 10,
    }


@app.post("/chat/stream")
def post_chat_stream(message: ChatMessage):
    """
    流式聊天接口 - Server-Sent Events

    使用说明：
    - POST 请求，body: {"content": "用户消息", "session_id": "可选"}
    - 返回 SSE 流式响应
    - 每个事件: data: {"content": "...", "done": false}\n\n
    - 结束事件: data: {"done": true, "current_step": N}\n\n
    """
    import json as _json
    import queue

    session_id = message.session_id or str(uuid.uuid4())

    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 100,
    }

    graph = get_graph()

    # 初始化或获取状态
    try:
        existing = graph.get_state(config)
        if existing is None or not existing.values:
            state = create_initial_state(session_id, message.member_id)
        else:
            state = dict(existing.values) if hasattr(existing, "values") else dict(existing)
    except Exception:
        state = create_initial_state(session_id, message.member_id)

    from langchain_core.messages import HumanMessage

    # Sync generator: blocking graph.stream() runs in ThreadPoolExecutor,
    # communicates via stdlib queue.Queue so StreamingResponse can iterate.
    def event_generator():
        q: queue.Queue = queue.Queue()
        CHUNK_TIMEOUT = 120  # seconds per chunk (LLM needs more time)

        def sync_worker():
            try:
                for chunk in graph.stream(
                    {
                        **state,
                        "messages": [HumanMessage(content=message.content)],
                    },
                    stream_mode="messages",
                    version="v2",
                    config=config,
                ):
                    q.put(chunk)
                q.put(None)  # Sentinel: stream ended
            except Exception as e:
                q.put({"__error": str(e)})
                q.put(None)

        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(sync_worker)

        try:
            current_step = 1
            last_message_count = 0
            prev_step_name = None

            while True:
                try:
                    chunk = q.get(timeout=CHUNK_TIMEOUT)
                except queue.Empty:
                    executor.shutdown(wait=False)
                    yield f"data: {_json.dumps({'error': 'AI响应超时（120秒），可能是模型服务暂时不可用，请稍后重试'})}\n\n"
                    break

                if chunk is None:
                    break  # Stream ended normally

                if isinstance(chunk, dict) and "__error" in chunk:
                    yield f"data: {_json.dumps({'error': chunk['__error']})}\n\n"
                    break

                # v2 format: {"type": "messages", "ns": (), "data": (message_chunk, metadata)}
                if isinstance(chunk, dict) and chunk.get("type") == "messages":
                    msg_chunk, metadata = chunk["data"]

                    # Filter by node if metadata available
                    node_name = metadata.get("langgraph_node", "") if metadata else ""

                    # Handle tool_calls in message chunk
                    if hasattr(msg_chunk, "tool_calls") and msg_chunk.tool_calls:
                        for tc in msg_chunk.tool_calls:
                            tc_payload = _json.dumps({
                                "name": tc.get("name", ""),
                                "arguments": tc.get("args", {}),
                            })
                            yield f"event: tool_calls\ndata: {tc_payload}\n\n"

                    # Handle content - skip system, human, and tool messages
                    if hasattr(msg_chunk, "content") and msg_chunk.content:
                        msg_type = getattr(msg_chunk, "type", None) or getattr(msg_chunk, "name", "ai")
                        if msg_type not in ("system", "SystemMessage", "human", "tool"):
                            content_payload = _json.dumps({
                                "content": msg_chunk.content,
                                "role": "assistant",
                            })
                            yield f"event: content\ndata: {content_payload}\n\n"

                    prev_step_name = node_name
                elif isinstance(chunk, dict) and chunk.get("type") == "updates":
                    # Node state updates - extract current_step
                    for node_name, node_data in chunk.get("data", {}).items():
                        if isinstance(node_data, dict) and "current_step" in node_data:
                            current_step = node_data["current_step"]
                else:
                    # Fallback: try older dict format
                    for step_name, step_result in chunk.items():
                        if isinstance(step_result, dict):
                            messages = step_result.get("messages", [])
                            if len(messages) > last_message_count:
                                new_messages = messages[last_message_count:]
                                for msg in new_messages:
                                    if hasattr(msg, "type") and msg.type == "ai" and hasattr(msg, "content"):
                                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                                            for tc in msg.tool_calls:
                                                tc_payload = _json.dumps({
                                                    "name": tc.get("name", ""),
                                                    "arguments": tc.get("args", {}),
                                                })
                                                yield f"event: tool_calls\ndata: {tc_payload}\n\n"
                                        if msg.content:
                                            content_payload = _json.dumps({
                                                "content": msg.content,
                                                "role": "assistant",
                                            })
                                            yield f"event: content\ndata: {content_payload}\n\n"
                                last_message_count = len(messages)
                            if "current_step" in step_result:
                                current_step = step_result["current_step"]
                        prev_step_name = step_name
                    continue

            # 结束事件
            step_name = STEP_DISPLAY_NAMES.get(STEP_NAMES[current_step - 1], STEP_NAMES[current_step - 1])
            yield f"event: done\ndata: {_json.dumps({'current_step': current_step, 'current_step_name': step_name, 'session_id': session_id})}\n\n"
        finally:
            executor.shutdown(wait=False)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/upload/{session_id}")
async def upload_evidence(
    session_id: str,
    file: UploadFile = File(...),
    evidence_item_id: str = Form(...),
):
    """
    证据文件上传接口
    """
    import uuid as uuid_lib

    uploads_dir = f"data/uploads/{session_id}"
    os.makedirs(uploads_dir, exist_ok=True)

    file_id = f"file_{uuid_lib.uuid4().hex[:12]}"
    safe_filename = f"{file_id}_{file.filename}"
    stored_path = f"{uploads_dir}/{safe_filename}"

    content = await file.read()
    with open(stored_path, "wb") as f:
        f.write(content)

    # 更新 graph 状态
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}

    try:
        state = graph.get_state(config)
        if state and hasattr(state, "values"):
            current_state = dict(state.values)
        else:
            current_state = dict(state) if state else {}
    except Exception:
        current_state = {}

    evidence_files = current_state.get("evidence_files") or {}
    from datetime import datetime
    file_ref = {
        "file_id": file_id,
        "filename": file.filename,
        "stored_path": stored_path,
        "uploaded_at": datetime.now().isoformat(),
        "evidence_item_id": evidence_item_id,
    }
    evidence_files[file_id] = file_ref

    # 更新证据项的文件引用
    evidence_items = current_state.get("evidence_items") or []
    for item in evidence_items:
        if item.get("id") == evidence_item_id:
            refs = item.get("uploaded_file_refs") or []
            refs.append(file_id)
            item["uploaded_file_refs"] = refs
            break

    graph.update_state(config, {
        "evidence_files": evidence_files,
        "evidence_items": evidence_items,
    })

    return {
        "file_id": file_id,
        "filename": file.filename,
        "stored_path": stored_path,
    }


class ReplayRequest(BaseModel):
    checkpoint_id: str


class HistoryEntry(BaseModel):
    checkpoint_id: str
    step: Optional[int]
    next_node: Optional[str]
    source: Optional[str]
    timestamp: Optional[str]


@app.get("/sessions/{session_id}/history")
def get_session_history(session_id: str) -> List[HistoryEntry]:
    """
    获取会话执行历史（所有 checkpoint 记录）。
    可用于前端展示时间线，让用户选择从哪个点重新执行。
    """
    config = {"configurable": {"thread_id": session_id}}
    graph = get_graph()

    try:
        history = list(graph.get_state_history(config))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"无法获取历史记录: {str(e)}")

    entries = []
    for state in history:
        cfg = state.config.get("configurable", {})
        checkpoint_id = cfg.get("checkpoint_id", "")
        metadata = getattr(state, "metadata", {}) or {}
        step = metadata.get("step")
        source = metadata.get("source")
        # 尝试从 values 中提取 timestamp
        values = getattr(state, "values", {}) or {}
        last_updated = values.get("last_updated")

        # next 字段：即将执行的节点（用于判断"停在哪儿了"）
        next_nodes = getattr(state, "next", None)

        entries.append(HistoryEntry(
            checkpoint_id=checkpoint_id,
            step=step,
            next_node=next_nodes[0] if next_nodes else None,
            source=source,
            timestamp=last_updated,
        ))

    return entries


@app.post("/sessions/{session_id}/replay")
def replay_session(session_id: str, body: ReplayRequest):
    """
    从指定 checkpoint 重新执行。

    - checkpoint_id: 从 /history 接口获取的 checkpoint_id
    - 返回重放后的最终状态

    注意：重放会重新执行 LLM 调用，消耗 API 配额。
    """
    config = {
        "configurable": {
            "thread_id": session_id,
            "checkpoint_id": body.checkpoint_id,
        },
        "recursion_limit": 100,
    }
    graph = get_graph()

    try:
        result = graph.invoke(None, config=config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"重放失败: {str(e)}")

    messages = result.get("messages", [])
    ai_message = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "ai":
            ai_message = msg.content
            break

    current_step = result.get("current_step", 1)

    return {
        "session_id": session_id,
        "checkpoint_id": body.checkpoint_id,
        "message": ai_message,
        "current_step": current_step,
        "current_step_name": STEP_DISPLAY_NAMES.get(STEP_NAMES[current_step - 1], STEP_NAMES[current_step - 1]),
    }


@app.post("/sessions/{session_id}/reset")
def reset_session(session_id: str):
    """重置会话（重新开始）"""
    config = {"configurable": {"thread_id": session_id}}
    graph = get_graph()

    try:
        graph.delete_session(config)
    except Exception:
        pass

    return {"status": "reset", "session_id": session_id}


@app.get("/steps")
def list_steps():
    """列出所有步骤"""
    return [
        {"step": i + 1, "name": name, "display_name": STEP_DISPLAY_NAMES.get(name, name)}
        for i, name in enumerate(STEP_NAMES)
    ]


# ============================================================================
# Run
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
