"""
九步劳动争议咨询系统 - 本地测试脚本

用于测试新的九步咨询流程，通过 graph.stream() 直接验证工作流。

测试模式：
1. 单步测试：测试单个步骤的 prompt 和工具
2. 完整流程测试：模拟用户选择"AI智能问答"后一路到底
3. 交互式测试：手动输入多轮对话
"""
import json
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage

from langgraph.types import Command
from langgraph_model.consultation_graph import (
    get_consultation_graph,
    STEP_NAMES,
    build_step_system_prompt,
    _build_step_node,
)
from langgraph_model.consultation_state import create_initial_state

# ============================================================================
# 测试配置
# ============================================================================

THREAD_ID = "test-local-001"


# ============================================================================
# 测试用例
# ============================================================================


def test_step1_selector_direct():
    """直接测试 step1_selector 节点"""
    print("=" * 70)
    print("测试: step1_selector 直接调用")
    print("=" * 70)

    node = _build_step_node("step1_selector")
    initial = create_initial_state(session_id=THREAD_ID)

    # 模拟用户选择 AI 咨询
    state = {
        **initial,
        "messages": [HumanMessage(content="我想用AI智能问答")],
    }

    result = node(state)
    print(f"节点返回: {len(result.get('messages', []))} 条消息")

    for msg in result.get("messages", []):
        if hasattr(msg, "content") and msg.content:
            content = msg.content[:300]
            print(f"[AI] {content}...")
            # 检查是否调用了工具
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"  工具调用: {[tc['name'] for tc in msg.tool_calls]}")

    print(f"goto 字段: {result.get('goto', '无')}")
    return result


def test_step2_initial_direct():
    """直接测试 step2_initial 节点"""
    print("=" * 70)
    print("测试: step2_initial 直接调用")
    print("=" * 70)

    node = _build_step_node("step2_initial")
    initial = create_initial_state(session_id=THREAD_ID)

    # step1 已经完成，用户选择案情描述
    state = {
        **initial,
        "current_step": 2,
        "messages": [
            HumanMessage(content="我想用AI智能问答"),
            HumanMessage(content="公司拖欠工资两个月了，我想维权"),
        ],
    }

    result = node(state)
    print(f"节点返回: {len(result.get('messages', []))} 条消息")

    for msg in result.get("messages", []):
        if hasattr(msg, "content") and msg.content:
            content = msg.content[:300]
            print(f"[AI] {content}...")

    print(f"goto 字段: {result.get('goto', '无')}")
    return result


def test_full_flow_with_auto_route():
    """测试完整流程：模拟用户一路选择默认选项直到结束"""
    print("=" * 70)
    print("测试: 完整流程（自动路由模式）")
    print("=" * 70)

    graph = get_consultation_graph()
    config = {
        "configurable": {"thread_id": THREAD_ID},
        "recursion_limit": 50,
    }

    # 模拟用户一路回复默认选项
    # 实际上我们需要多轮输入，每轮用户回答后才会调用 proceed_to_next_step
    # 这里我们模拟第一轮输入

    messages = [
        HumanMessage(content="我想用AI智能问答"),  # step1 选择
    ]

    # 手动循环执行每一步
    current_step = 1
    max_iterations = 20

    for i in range(max_iterations):
        print(f"\n--- 迭代 {i + 1}: 当前步骤 {current_step} ---")

        if current_step > len(STEP_NAMES):
            print("流程结束")
            break

        step_name = STEP_NAMES[current_step - 1]
        node = _build_step_node(step_name)

        # 构造状态
        state = {
            "messages": messages,
            "current_step": current_step,
            "completed_steps": set(range(1, current_step)),
            "step_data": {},
            "dirty_steps": set(),
            "case_category": None,
            "session_id": THREAD_ID,
        }

        # 调用节点
        result = node(state)

        # 提取 AI 消息
        ai_messages = [m for m in result.get("messages", []) if hasattr(m, "type") and m.type == "ai"]
        if ai_messages:
            last_ai = ai_messages[-1]
            content = getattr(last_ai, "content", "")[:200]
            print(f"[{step_name}] AI: {content}...")

            # 检查工具调用
            tool_calls = getattr(last_ai, "tool_calls", []) or []
            if tool_calls:
                print(f"  工具调用: {[tc.get('name') or tc.get('function', {}).get('name') for tc in tool_calls]}")

            messages.append(last_ai)
        else:
            print(f"[{step_name}] 无 AI 消息返回")

        # 检查 goto
        goto = result.get("goto")
        if goto:
            if goto == END:
                print("流程结束 (goto=END)")
                break
            # 找到下一个步骤
            if goto in STEP_NAMES:
                current_step = STEP_NAMES.index(goto) + 1
                print(f"跳转到步骤: {goto} (step {current_step})")
            else:
                print(f"未知 goto: {goto}")
                break
        else:
            # 没有 goto，检查 current_step 是否变化
            new_step = result.get("current_step", current_step)
            if new_step != current_step:
                current_step = new_step
                print(f"步骤推进到: {current_step}")
            else:
                # 没有进展，可能是等待用户输入
                print("等待用户输入...")
                # 模拟用户输入继续
                user_input = _get_default_user_input(current_step, messages)
                if user_input:
                    messages.append(HumanMessage(content=user_input))
                    print(f"[用户] {user_input}")
                else:
                    print("无法自动生成用户输入，停止")
                    break

    print("\n完成！")


def _get_default_user_input(step: int, messages: list) -> str:
    """根据当前步骤获取默认用户输入"""
    # 简化版本：直接跳过复杂流程
    defaults = {
        1: "我想用AI智能问答",
        2: "欠薪",  # 用户选择案由
        3: "在职",  # Q1: 就业状态
        4: "继续",  # 跳过剩余问题
        5: "继续",  # 跳过特殊问题
        6: "继续",  # 跳过证据
        7: "继续",  # 跳过风险评估
        8: "继续",  # 跳过文书
        9: "继续",  # 跳过路线图
        10: "完成",
    }
    return defaults.get(step, "继续")


def test_stream_single_turn():
    """测试 graph.stream() 单轮执行（展示工作流行为）"""
    print("=" * 70)
    print("测试: graph.stream() 单轮执行")
    print("=" * 70)

    graph = get_consultation_graph()
    config = {
        "configurable": {"thread_id": THREAD_ID},
        "recursion_limit": 30,
    }

    initial = create_initial_state(session_id=THREAD_ID)

    print(f"初始状态: step={initial['current_step']}")

    all_chunks = []
    try:
        for i, chunk in enumerate(graph.stream(
            {
                **initial,
                "messages": [HumanMessage(content="我想用AI智能问答")],
            },
            config=config,
        )):
            all_chunks.append(chunk)
            for step_name, result in chunk.items():
                print(f"Chunk {i}: {step_name}")
                if isinstance(result, dict):
                    if "goto" in result:
                        print(f"  goto: {result['goto']}")
                    msgs = result.get("messages", [])
                    print(f"  messages: {len(msgs)}")
                    for msg in msgs:
                        if hasattr(msg, "content") and msg.content:
                            print(f"    [{type(msg).__name__}] {msg.content[:100]}...")

        print(f"\n总 chunk 数: {len(all_chunks)}")

    except Exception as e:
        print(f"错误: {e}")


# ============================================================================
# 主入口
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "step1":
            test_step1_selector_direct()
        elif test_name == "step2":
            test_step2_initial_direct()
        elif test_name == "stream":
            test_stream_single_turn()
        elif test_name == "full":
            test_full_flow_with_auto_route()
        else:
            print(f"未知测试: {test_name}")
    else:
        # 运行所有测试
        test_step1_selector_direct()
        print("\n\n")
        test_step2_initial_direct()
        print("\n\n")
        test_stream_single_turn()
