"""
九步咨询系统 - 交互式测试

用法：
    python test_interactive.py
"""
from langgraph_model.consultation_graph import get_consultation_graph
from langchain_core.messages import HumanMessage

graph = get_consultation_graph()
config = {"configurable": {"thread_id": "interactive"}, "recursion_limit": 200}

print("九步咨询系统 - 交互测试\n")

while True:
    user_input = input("你: ").strip()
    if not user_input:
        continue
    if user_input.lower() in ("q", "quit", "退出"):
        break

    for part in graph.stream({"messages": [HumanMessage(content=user_input)]}, 
                            stream_mode="updates",
                            version="v2",
                            config=config):
            # print(part["type"])  # "updates"
            # print(part["ns"])    # ()
            # print(part["data"][0])  # {"node_name": {"key": "value"}}
            if part["type"] == "updates":
            # UpdatesStreamPart — only the changed keys from each node
                for node_name, state in part["data"].items():
                    print(f"Node `{node_name}` updated: {state}")
            elif part["type"] == "messages":
                # MessagesStreamPart — (message_chunk, metadata) from LLM calls
                msg, metadata = part["data"]
                print(msg.content, end="", flush=True)
