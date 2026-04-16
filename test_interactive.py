"""
九步咨询系统 - 交互式测试脚本

用法：
    python test_interactive.py

每次提示时输入你的回复，按 q/quit 退出。
"""
from langgraph_model.consultation_graph import get_consultation_graph
from langgraph_model.consultation_state import create_initial_state
from langchain_core.messages import HumanMessage

STEP_NAMES = [
    "step1_selector", "step2_initial", "step3_common", "step4_special",
    "step5_qualification", "step6_evidence", "step7_risk", "step8_documents",
    "step9_roadmap", "step10_review",
]
STEP_DISPLAY = {
    "step1_selector": "模式选择",
    "step2_initial": "问题初判",
    "step3_common": "通用问题",
    "step4_special": "特殊问题",
    "step5_qualification": "案件定性",
    "step6_evidence": "证据攻略",
    "step7_risk": "风险提示",
    "step8_documents": "文书生成",
    "step9_roadmap": "行动路线图",
    "step10_review": "求助复核",
}


def get_step_display(step_num):
    if 1 <= step_num <= 10:
        return STEP_DISPLAY.get(STEP_NAMES[step_num - 1], f"步骤{step_num}")
    return f"步骤{step_num}"


def main():
    print("=" * 60)
    print("九步咨询系统 - 交互测试")
    print("=" * 60)
    print("输入 q/quit 退出\n")

    graph = get_consultation_graph()
    config = {"configurable": {"thread_id": "interactive-test"}, "recursion_limit": 200}

    state = create_initial_state("interactive-test")

    step = 1
    while True:
        user_input = input(f"\n[{get_step_display(step)}] 你: ").strip()
        if user_input.lower() in ("q", "quit", "退出"):
            print("\n再见！")
            break

        if not user_input:
            continue

        try:
            result = graph.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
            )
        except Exception as e:
            print(f"\n错误: {e}")
            continue

        # 打印 AI 回复
        ai_messages = [
            m for m in result.get("messages", [])
            if hasattr(m, "content") and m.content
            and not str(m.content).startswith("Command")
        ]
        if ai_messages:
            last_ai = ai_messages[-1]
            content = last_ai.content
            print(f"\nAI: {content}")

        # 更新当前步骤
        step = result.get("current_step", step)
        print(f"[当前: {get_step_display(step)}]")

        # 如果到达最后一步
        if step > 10:
            print("\n流程结束！")
            break


if __name__ == "__main__":
    main()
