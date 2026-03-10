import json
from langchain_core.messages import HumanMessage
from langchain_core.messages import BaseMessage,convert_to_openai_messages
from langgraph_model.legal_assistant import graph 
from langgraph_model.legal_workflow import create_extractor_graph, create_summarizer_graph

extractor_graph = create_extractor_graph()
summarizer_graph = create_summarizer_graph()
config = {
    "configurable": {
        "thread_id": "114"
    },
    "recursion_limit": 3000
}
# STREAM_MODE =  "update"
STREAM_MODE = "values"
# STREAM_MODE = "messages"

## 初次请求
request = {
        "history_list": [],
        "query": "你好，我想咨询一下，我孩子去游乐场玩，玩碰碰车时候孩子手腕骨折，游乐场应该承担什么责任？",
        "thread_id": "114"
    }
# request = {
#         "history_list": [],
#         "query": "我在工厂上班时手被机器压伤了，现在医生说情况挺严重的。我一个月工资才三千多，现在不能上班了，家里老人孩子都指着我呢。厂里说给我报了工伤，但是后续的治疗费、误工费这些到底怎么算，我完全搞不明白。请问按照规定应该怎么赔偿？",
#         "thread_id": "114"
#     }

# request ={
#     "query": "我的情况符合情景1",
#     "history_list": [
#         {
#             "role": "user",
#             "content": "我想离婚，但是对方不同意，还威胁我，孩子才3岁，我该怎么办?"
#         },
#         {
#             "role": "assistant",
#             "content": "根据《中华人民共和国民法典》第一千零七十九条的规定，夫妻一方要求离婚的，可以向人民法院提起离婚诉讼。法院会根据夫妻感情是否确已破裂进行判决。对于您提到的威胁行为，您可以收集相关证据，例如录音、短信等，并向公安机关报案，以保障自身安全。\n\n关于孩子的抚养权问题，法院会根据有利于孩子成长的原则进行判决，通常会考虑双方的经济能力、生活环境以及对孩子的照顾能力等因素。根据《民法典》第一千零八十四条，离婚后，父母对子女仍有抚养、教育、保护的权利和义务。\n\n建议您在处理离婚及抚养权问题时，寻求专业律师的帮助，以便更好地维护您的合法权益。"
#         },
#         {
#             "role": "assistant",
#             "content": "[\n    {\"name\":\"情形1：对方有家暴行为，您有相关证据（如伤情照片、医院诊断、报警记录等）\", \n    \"description\":\"在离婚诉讼中，家暴是法定离婚事由，法院通常会判决离婚。这种情况下，您不仅可以提起离婚诉讼，还可以： 1. 申请人身安全保护令，禁止对方接近您和孩子 2. 要求精神损害赔偿\", \n    \"advice\":\"立即申请人身保护令，同时准备离婚诉讼\"},\n    \n    {\"name\":\"情形2：对方不同意离婚并威胁您，但没有家暴证据\", \n    \"description\":\"在这种情况下，您可以收集对方威胁的证据（如录音、短信等），并向法院提起离婚诉讼。法院会根据夫妻感情是否确已破裂进行判决。您也可以向公安机关报案，以保障自身安全。\", \n    \"advice\":\"收集威胁证据，向法院提起离婚诉讼，并向公安机关报案\"},\n    \n    {\"name\":\"情形3：对方不同意离婚，且孩子抚养权存在争议\", \n    \"description\":\"法院会根据有利于孩子成长的原则进行判决，通常会考虑双方的经济能力、生活环境以及对孩子的照顾能力等因素。您可以准备相关证据证明您更适合抚养孩子，例如收入证明、居住环境照片、对孩子的照顾记录等。\", \n    \"advice\":\"准备抚养权相关证据，向法院提起离婚诉讼\"}\n]"
#         }
#     ],
#     "thread_id": "thread_123"
# }


inputs = []
# 添加历史消息
for msg in request['history_list']:
        inputs.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
# 添加当前用户输入
inputs.append({
    "role": "user",
    "content": request['query']
})
langchain_messages = []
from langchain_core.messages import AIMessage,HumanMessage
for msg in inputs:
    if msg['role'] == 'assistant':
        langchain_messages.append(AIMessage(content=msg['content']))
    elif msg['role'] == 'user':
        langchain_messages.append(HumanMessage(content=msg['content']))
# 创建配置，使用传入的thread_id
config = {
    "configurable": {
        "thread_id": request['thread_id']
    },
    "recursion_limit": 3000
}
json_buffer = ''
for namespace, event in graph.stream(
    {"messages": langchain_messages},
    config=config,
    subgraphs=True,
    stream_mode=STREAM_MODE,
    debug=False
):
    if STREAM_MODE == 'values':
        msg = event['messages'][-1]
        content = msg.content if isinstance(msg, BaseMessage) else msg['content']
        
        sse_data = {
            "type": "content",
            "data": content
        }
        print( f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n")
        
    elif STREAM_MODE == 'messages':
        msg_chunk, meta_data = event

        if msg_chunk.name is not None:
            continue
        name = meta_data['langgraph_node']

        if name == 'process_selection'  and meta_data.get('ls_model_name') is not None:
            continue   ##### 过滤掉监督者节点模型选择的消息

        if name in ['detailer','advisor']:
            json_buffer += msg_chunk.content
            try:
                json_data = json.loads(json_buffer)
                # print(json_data)
                json_buffer = ''
                sse_data = {
                    "type": "json",
                    "data": {'content':json_data,
                            "additional_kwargs": {},
                            "response_metadata": {},
                            "type": "AIMessageChunk",
                            "name": name}
                }
            except json.JSONDecodeError:
                continue
        else:
            sse_data = {
                "type": "chunk",
                "data": msg_chunk.model_dump()
            }
            sse_data["data"]["name"] = name

        print(f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n")
        
    print("=========================================================================")

print("完成！")




# for namespace, event in graph.stream(
#     {"messages": langchain_messages},
#     config=config,
#     subgraphs=True,
#     stream_mode=STREAM_MODE,
#     debug=False
# ):
#     if STREAM_MODE == 'values':
#         msg = event['messages'][-1]
#         content = msg.content if isinstance(msg, BaseMessage) else msg['content']
        
#         sse_data = {
#             "type": "content",
#             "data": content
#         }
#         print( f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n")
        
#     elif STREAM_MODE == 'messages':
#         msg_chunk, meta_data = event

#         if msg_chunk.name is not None:
#             continue
#         name = meta_data['langgraph_node']

#         if name == 'process_selection'  and meta_data.get('ls_model_name') is not None:
#             continue   ##### 过滤掉监督者节点模型选择的消息

#         if name in ['detailer','advisor']:
#             json_buffer += msg_chunk.content
#             try:
#                 json_data = json.loads(json_buffer)
#                 # print(json_data)
#                 json_buffer = ''
#                 sse_data = {
#                     "type": "json",
#                     "data": {'content':json_data,
#                             "additional_kwargs": {},
#                             "response_metadata": {},
#                             "type": "AIMessageChunk",
#                             "name": name}
#                 }
#             except json.JSONDecodeError:
#                 continue
#         else:
#             sse_data = {
#                 "type": "chunk",
#                 "data": msg_chunk.model_dump()
#             }
#             sse_data["data"]["name"] = name

#         print(f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n")
        
#     print("=========================================================================")

# print("完成！")