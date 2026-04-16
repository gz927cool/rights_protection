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
from langgraph.checkpoint.memory import InMemorySaver

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

_checkpointer = InMemorySaver()

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
        if existing is None:
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
        if hasattr(msg, "type") and msg.type == "ai":
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
        if existing is None:
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
        CHUNK_TIMEOUT = 30  # seconds per chunk

        def sync_worker():
            try:
                for chunk in graph.stream(
                    {
                        **state,
                        "messages": [HumanMessage(content=message.content)],
                    },
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
                    yield f"data: {_json.dumps({'error': 'AI响应超时（30秒），可能是模型服务暂时不可用，请稍后重试'})}\n\n"
                    break

                if chunk is None:
                    break  # Stream ended normally

                if isinstance(chunk, dict) and "__error" in chunk:
                    yield f"data: {_json.dumps({'error': chunk['__error']})}\n\n"
                    break

                # chunk = {"step_name": node_output}
                for step_name, step_result in chunk.items():
                    # 如果同一个 step 再次出现，说明它在等待用户输入，停止 stream
                    if prev_step_name == step_name and prev_step_name is not None:
                        break

                    if isinstance(step_result, dict):
                        messages = step_result.get("messages", [])

                        # Only process NEW messages (messages added since last chunk)
                        if len(messages) > last_message_count:
                            new_messages = messages[last_message_count:]
                            for msg in new_messages:
                                if (
                                    hasattr(msg, "type")
                                    and msg.type == "ai"
                                    and hasattr(msg, "content")
                                    and msg.content
                                ):
                                    content = msg.content
                                    payload = _json.dumps({"content": content, "done": False})
                                    yield f"data: {payload}\n\n"
                            last_message_count = len(messages)

                        # 更新 current_step
                        if "current_step" in step_result:
                            current_step = step_result["current_step"]

                    prev_step_name = step_name
                else:
                    # Inner loop completed normally, continue to next chunk
                    continue
                # Inner loop broke (same step repeated), break outer loop too
                break

            # 结束事件
            yield f"data: {_json.dumps({'done': True, 'current_step': current_step, 'session_id': session_id})}\n\n"
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
