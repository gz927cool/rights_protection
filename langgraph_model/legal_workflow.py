from typing import Dict, TypedDict, List, Tuple, Optional, Annotated
from langgraph.graph import StateGraph, END, START
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from typing_extensions import TypedDict, Literal
import json
import os
import uuid
from langchain_core.output_parsers import JsonOutputParser

from langgraph_model.prompts import EXTRACTOR_PROMPT,SUMMARIZER_PROMPT
from langgraph_model.state import AgentState
from langgraph_model.load_cfg import OPENAI_API_KEY,MODEL_NAME,BASE_URL
# 创建不同角色的模型实例
model = ChatOpenAI(model=MODEL_NAME , api_key=OPENAI_API_KEY,base_url=BASE_URL, temperature=0, max_tokens=4096)

def create_extractor_graph():
    # 总结者节点
    def extractor_node(state: AgentState) -> AgentState:
        prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTOR_PROMPT),
            MessagesPlaceholder(variable_name="messages")
        ])
        agent = prompt|model

        ### 解决DeeepSeek无法正确处理JSON输出的沙雕问题
        messages = state["messages"] + [HumanMessage(content="Please directly output the JSON content without any explanatory or descriptive statements.Do not surround the JSON with ``` or any other markup — output raw JSON only.")]
        temp_state = state.copy()
        temp_state["messages"] = messages

        response = agent.invoke(temp_state)
        ai_message = AIMessage(content=response.content,name='extractor')
        state["messages"].append(ai_message)
        return state

    # 创建工作流
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_edge(START, "extractor")
    workflow.add_node("extractor", extractor_node)
    workflow.add_edge("extractor", END)


    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory
    )
def create_summarizer_graph():
    # 总结者节点
    def summarizer_node(state: AgentState) -> AgentState:
        prompt = ChatPromptTemplate.from_messages([
            ("system", SUMMARIZER_PROMPT),
            MessagesPlaceholder(variable_name="messages")
        ])
        agent = prompt|model
        response = agent.invoke(state)
        ai_message = AIMessage(content=response.content,name='extractor')
        state["messages"].append(ai_message)
        return state

    # 创建工作流
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_edge(START, "summarizer")
    workflow.add_node("summarizer", summarizer_node)
    workflow.add_edge("summarizer", END)


    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory
    )