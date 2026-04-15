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
from json_repair import repair_json
from langgraph_model.prompts import ANSWERER_PROMPT,DETAILER_PROMPT,ADVISOR_PROMPT,PROCESS_SELECTION_PROMPT,LEGAL_SERVICES,SUMMARIZER_PROMPT
from langgraph_model.state import AgentState,InputState
from langgraph_model.load_cfg import OPENAI_API_KEY,MODEL_NAME,BASE_URL
# 创建不同角色的模型实例
model = ChatOpenAI(model=MODEL_NAME , api_key=OPENAI_API_KEY,base_url=BASE_URL, temperature=0, max_tokens=4096)

    
# 解答者节点
def answerer_node(state: AgentState) -> AgentState:
    prompt = ChatPromptTemplate.from_messages([
        ("system", ANSWERER_PROMPT),
        MessagesPlaceholder(variable_name="messages")
    ])
    agent = prompt|model
    response = agent.invoke(state)
    ai_message = AIMessage(content=response.content,name='answerer')
    return {"messages": [ai_message]}

# 总结者节点
def summarizer_node(state: AgentState) -> AgentState:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SUMMARIZER_PROMPT),
        MessagesPlaceholder(variable_name="messages")
    ])
    agent = prompt|model
    response = agent.invoke(state)
    ai_message = AIMessage(content=response.content,name='summarizer')
    return {"messages": [ai_message]}

# 细节补充者节点
def detailer_node(state: AgentState) -> AgentState:   
    model = ChatOpenAI(model=MODEL_NAME , api_key=OPENAI_API_KEY,base_url=BASE_URL, temperature=0, max_tokens=4096)
                    #    response_format={"type": "json_object"})
    messages = state["messages"] + [HumanMessage(content="继续")]
    prompt = ChatPromptTemplate.from_messages([
        ("system", DETAILER_PROMPT),
        MessagesPlaceholder(variable_name="messages")
        # *[(m["role"], m["content"]) for m in state["messages"]]
    ])
    temp_state = state.copy()
    temp_state["messages"] = messages
    agent = prompt|model #|JsonOutputParser()
    response = agent.invoke(temp_state)
    # response_extracted = repair_json(response.content,ensure_ascii=False)
    # ai_message = AIMessage(content=response_extracted,name='detailer')
    ai_message = AIMessage(content=response.content,name='detailer')
    
    return {"messages": [ai_message]}


# 处置建议者节点
def advisor_node(state: AgentState) -> AgentState:
    messages_data = state['messages']
    langchain_messages = []
    prompt = ChatPromptTemplate.from_messages([
        ("system", ADVISOR_PROMPT.replace('{services}',LEGAL_SERVICES)),
        MessagesPlaceholder(variable_name="messages")
    ])
    agent = prompt| model

    ### 解决DeeepSeek无法正确处理JSON输出的沙雕问题
    # messages = state["messages"] + [HumanMessage(content="Please directly output the JSON content without any explanatory or descriptive statements.Do not surround the JSON with ``` or any other markup — output raw JSON only.")]
    # messages = state["messages"]
    # temp_state["messages"] = messages
    # temp_state['messages'][-1].content = temp_state['messages'][-1].content + "Please directly output the JSON content without any explanatory or descriptive statements.Do not surround the JSON with ``` or any other markup — output raw JSON only."   ## 加在这里对deepseekV3无效

    response = agent.invoke(state)
    # response_extracted = repair_json(response.content,ensure_ascii=False)
    # ai_message = AIMessage(content=response_extracted,name='advisor')
    ai_message = AIMessage(content=response.content,name='advisor')

    state["messages"].append(ai_message)
    
    return state

# 人类干预节点
def human_node(state: AgentState) -> AgentState:
    feedback = interrupt("please provide feedback")
    return {"messages": [HumanMessage(content=feedback)]}


# 处理用户选择的节点
def process_selection(state: AgentState)-> Command[Literal["detailer","advisor","answerer","summarizer", "__end__"]]:
    messages = state["messages"]
    prompt = ChatPromptTemplate.from_messages([
        ("system", PROCESS_SELECTION_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
        # ("user", "现在，请选择下一个执行的的模块或等待用户输入")
        ]
        )
    agent = prompt|model
    response = agent.invoke(state)
        
    # 从响应中提取选择（只保留一个简单的字符串匹配）
    response_text = response.content.strip().lower()
        
    # 设置默认值
    next_node = "human"  # 默认交给解答者
        
    # 根据响应内容确定下一个节点
    if "advisor" in response_text:
        next_node = "advisor"
        task = "推荐可能用的法律服务。"
    elif "detailer" in response_text:
        next_node = "detailer"
        task = "对可能遇到的情景进行分析。"
    elif "answerer" in response_text:
        next_node = "answerer"
        task = "回答问题。"
    elif "summarizer" in response_text:
        next_node = "summarizer"
        task = "总结问题。"
    else:
        next_node = "human"
        
    # 将选择存储在state中
    goto = next_node
    if goto == "human":
        goto = END
        return Command(goto=goto)
    elif goto=='summarizer':
        return Command(goto=goto)  ## 总结不需要加入额外信息来帮助Agent定位流程阶段
    else:
        return Command(goto=goto)  ## 总结不需要加入额外信息来帮助Agent定位流程阶段

    # return state


# 创建工作流
workflow = StateGraph(AgentState,input_schema=InputState)
    
# 添加节点
workflow.add_node("answerer", answerer_node)
workflow.add_node("detailer", detailer_node)
workflow.add_node("advisor", advisor_node)
workflow.add_node("summarizer", summarizer_node)
workflow.add_node("process_selection", process_selection)
    

workflow.add_edge(START, "process_selection")
    
analysis_nodes = [ "advisor", "answerer"]
for node in analysis_nodes:
    workflow.add_edge(node, "process_selection")
workflow.add_edge("detailer", END)
workflow.add_edge("summarizer", END)
    
memory = MemorySaver()
    
graph = workflow.compile(
        checkpointer=memory
    )
