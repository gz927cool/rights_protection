from fastapi import FastAPI, HTTPException, Request, APIRouter
import uvicorn
import os
import json
import time
import uuid
import logging
from starlette.responses import StreamingResponse, JSONResponse
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing import List, Dict, Any, Optional, Literal, AsyncGenerator
from fastapi.middleware.cors import CORSMiddleware
from langgraph_model.load_cfg import STREAM_MODE
# from langgraph_model.legal_assistant import graph
from langgraph_model.legal_supervisor import supervisor_agent as graph
from langgraph_model.legal_workflow import create_extractor_graph, create_summarizer_graph

graph = graph
extractor_graph = create_extractor_graph()
summarizer_graph = create_summarizer_graph()


class ChatCompletionMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    messages: List[ChatCompletionMessage]
    model: Optional[str] = None
    sessionId: Optional[str] = None
    stream: bool = Field(default=False)
    temperature: Optional[float] = Field(default=0.7)
    # OpenAI 标准参数补充
    model_config = ConfigDict(extra="allow")
    frequency_penalty: Optional[float] = Field(default=0.0)
    presence_penalty: Optional[float] = Field(default=0.0)
    top_p: Optional[float] = Field(default=1.0)
    max_tokens: Optional[int] = Field(default=None)

# 创建一个FastAPI应用程序实例
app = FastAPI(
    title="维权",
    version="1.0.0"
)

# 创建带有/myproject前缀的路由器
router = APIRouter()

logger = logging.getLogger("uvicorn.error")
access_logger = logging.getLogger("uvicorn.access")


# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或者指定 ["http://localhost:3000"] 之类
    allow_credentials=True,
    allow_methods=["*"],  # 或指定 ["POST", "GET"]
    allow_headers=["*"],  # 允许的自定义头部
)

def _select_graph(model_name: str):
    if model_name in {"extractor"}:
        return extractor_graph
    if model_name in {"summarizer"}:
        return summarizer_graph
    return graph


def _openai_chunk(
    *,
    completion_id: str,
    created: int,
    model: str,
    delta: Dict[str, Any],
    finish_reason: Optional[str] = None
) -> Dict[str, Any]:
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason
            }
        ]
    }


async def _langgraph_text_generator(request: ChatCompletionRequest, graph_instance, completion_id: str) -> AsyncGenerator[str, None]:
    """核心的文本生成器（提取异步文本逻辑），剥离OpenAI格式封装"""
    inputs: List[Dict[str, Any]] = []
    # 如果客户端负责管理状态且带上了历史记录，可以将所有的历史提供，不需保存重放。
    for m in request.messages:
        inputs.append({"role": m.role, "content": m.content})

    thread_id = request.sessionId or completion_id
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 3000
    }

    assembled_text = ""
    async for namespace, event in graph_instance.astream(
        {"messages": inputs},
        config=config,
        subgraphs=True,
        stream_mode=STREAM_MODE,
        debug=False
    ):
        if STREAM_MODE == "values":
            msg = event.get("messages", [])[-1] if isinstance(event, dict) else event["messages"][-1]
            content = msg.content if isinstance(msg, BaseMessage) else msg.get("content")
            if not content:
                continue
            delta_text = content[len(assembled_text):] if content.startswith(assembled_text) else content
            if not delta_text:
                continue
            assembled_text += delta_text
            yield delta_text
            continue

        try:
            msg_chunk, meta_data = event
        except (TypeError, ValueError):
            continue

        node_name = meta_data.get("langgraph_node")
        if node_name == "process_selection" and meta_data.get("ls_model_name") is not None:
            continue

        content = getattr(msg_chunk, "content", None)
        if content is None:
            if hasattr(msg_chunk, "model_dump"):
                content = msg_chunk.model_dump().get("content")
            elif isinstance(msg_chunk, dict):
                content = msg_chunk.get("content")

        if not content:
            continue

        delta_text = content[len(assembled_text):] if content.startswith(assembled_text) else content
        if not delta_text:
            continue
            
        assembled_text += delta_text
        yield delta_text


async def _stream_chat_completions(request: ChatCompletionRequest, graph_instance, completion_id: str, created: int):
    # 发送 initial chunk 表示 assistant 的 role
    yield f"data: {json.dumps(_openai_chunk(completion_id=completion_id, created=created, model=request.model, delta={'role': 'assistant'}), ensure_ascii=False)}\n\n"

    async for delta_text in _langgraph_text_generator(request, graph_instance, completion_id):
        chunk = _openai_chunk(completion_id=completion_id, created=created, model=request.model, delta={"content": delta_text})
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    # 关闭 chunk
    final_chunk = _openai_chunk(completion_id=completion_id, created=created, model=request.model, delta={}, finish_reason="stop")
    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    graph_instance = _select_graph(request.model)
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    if request.stream:
        return StreamingResponse(
            _stream_chat_completions(request, graph_instance, completion_id, created),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )

    content_parts: List[str] = []
    async for delta_text in _langgraph_text_generator(request, graph_instance, completion_id):
        content_parts.append(delta_text)
        
    full_content = "".join(content_parts)
    
    prompt_text = "".join([m.content for m in request.messages])
    prompt_tokens = len(prompt_text) // 2 or 1
    completion_tokens = len(full_content) // 2 or 1
    total_tokens = prompt_tokens + completion_tokens

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": full_content},
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
    }

app.include_router(router, prefix="/agent-ai-weiquan")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("API_PORT", 7777)), workers=1)
