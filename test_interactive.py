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

    result = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config=config)
    for msg in result["messages"]:
        msg.pretty_print()

    # msgs = result.get("messages", [])
    # for msg in reversed(msgs):
    #     if hasattr(msg, "content") and msg.content and not str(msg.content).startswith("Command"):
    #         print(f"AI: {msg.content}\n")
    #         break
