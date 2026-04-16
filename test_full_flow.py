"""
九步劳动争议咨询系统 - 完整流程测试

测试目标：模拟用户选择"欠薪"案由，一路走到 step5_qualification（案件定性）
验证流程正确，qualification 不为空

使用方法：
    set PYTHONIOENCODING=utf-8 && python test_full_flow.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph_model.consultation_graph import (
    create_consultation_graph,
    build_step_system_prompt,
)
from langgraph_model.consultation_state import create_initial_state, STEP_NAMES, STEP_DISPLAY_NAMES

# ============================================================================
# 测试配置
# ============================================================================

THREAD_ID = "test-full-flow-001"

# 模拟用户输入序列 (严格按流程顺序)
# Step2: 问题初判 - 先输入案由，再输入路径
USER_INPUTS_STEP2 = [
    "欠薪",    # 案由关键词
    "B",       # 路径选择: 自由描述案情
]

# Step3: 通用12问
USER_INPUTS_STEP3 = [
    "在职",        # Q1: 就业状态
    "已签合同",    # Q3: 签订劳动合同 (Q2跳过因为Q1=在职)
    "12000元",     # Q4: 月工资
    "银行转账",    # Q5: 工资发放方式
    "全部缴纳",    # Q6: 社保缴纳
    "职员",        # Q7: 工作岗位
    "2021年3月",   # Q8: 入职时间
    "有加班",      # Q9: 每周工作时间
    "欠薪,加班费", # Q10: 涉及诉求
    "20000元",     # Q11: 涉及金额
    "拿钱走人",    # Q12: 期望结果
]

# Step4: 特殊问题 - 跳过
USER_INPUTS_STEP4 = [
    "跳过",
]

# Step5: 案件定性 - 确认准确
USER_INPUTS_STEP5 = [
    "准确",
]


def print_separator(title: str = ""):
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def get_qualification_from_state(state):
    """
    从状态中获取 qualification。
    qualification 可能位于:
    1. state['qualification'] (顶层)
    2. state['step_data']['step5_qualification']['extra']['qualification']
    """
    # 直接检查顶层
    if state.get('qualification'):
        return state['qualification']

    # 检查 step_data 中
    step_data = state.get('step_data', {})
    step5 = step_data.get('step5_qualification', {})
    extra = step5.get('extra', {})
    if extra.get('qualification'):
        return extra['qualification']

    return None


def run_test():
    """执行完整流程测试"""
    print_separator("九步咨询系统 - 完整流程测试")
    print(f"线程ID: {THREAD_ID}")
    print(f"测试目标: 模拟用户选择'欠薪'案由，一路走到 step5_qualification")

    # 创建新的 graph 实例（无持久化 checkpointer）
    graph = create_consultation_graph()
    config = {
        "configurable": {"thread_id": THREAD_ID},
        "recursion_limit": 100,
    }

    # 创建初始状态
    initial_state = create_initial_state(session_id=THREAD_ID)
    state = dict(initial_state)
    state['messages'] = []

    step_results = []
    test_passed = True

    print_separator("开始执行流程")

    # 合并所有用户输入
    all_user_inputs = USER_INPUTS_STEP2 + USER_INPUTS_STEP3 + USER_INPUTS_STEP4 + USER_INPUTS_STEP5
    input_idx = 0

    max_iterations = 60
    for iteration in range(max_iterations):
        current_step = state.get('current_step', 1)

        if current_step > len(STEP_NAMES):
            print(f"[完成] 已到达流程末端 (step {current_step})")
            break

        step_name = STEP_NAMES[current_step - 1]
        step_display = STEP_DISPLAY_NAMES.get(step_name, step_name)

        # 获取当前步骤的 qualification（用于检查）
        current_qual = get_qualification_from_state(state)

        # 检查目标达成
        if current_step == 5 and current_qual:
            print_separator("验证通过")
            print(f"  qualification 已生成!")
            qual = current_qual
            cf = qual.get('case_facts', '')
            print(f"  case_facts: {cf[:100]}..." if len(cf) > 100 else f"  case_facts: {cf}")
            print(f"  case_types: {qual.get('case_types', [])}")
            rights = qual.get('rights_list', [])
            print(f"  权益清单 ({len(rights)} 项):")
            for r in rights[:5]:
                rn = r.get('right_name', '')
                am = r.get('amount', 0)
                print(f"    - {rn}: {am}元")
            break

        if input_idx >= len(all_user_inputs):
            print("[警告] 用户输入已用完")
            break

        user_input = all_user_inputs[input_idx]
        input_idx += 1

        print_separator(f"Step {current_step}: {step_display}")
        print(f"[用户输入 {input_idx}/{len(all_user_inputs)}]: {user_input}")

        # 追加用户消息
        state['messages'] = state.get('messages', []) + [HumanMessage(content=user_input, type="human")]

        # 移除 ToolMessage 对象（它们会导致API错误）
        # 但保留 AI 消息的 tool_calls=None 形式（不是真正的 ToolMessage）
        messages = state.get('messages', [])
        cleaned = []
        seen_ai = False

        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'tool':
                # 跳过 ToolMessage，但标记我们需要一个不带 tool_calls 的 AI 消息
                continue
            cleaned.append(msg)
            if hasattr(msg, 'type') and msg.type == 'ai':
                seen_ai = True

        # 如果有 AI 消息带有 tool_calls 但没有对应的 ToolMessage，
        # 需要将其替换为不带 tool_calls 的版本
        if seen_ai:
            final_msgs = []
            for msg in cleaned:
                if hasattr(msg, 'type') and msg.type == 'ai' and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # 这个AI消息有tool_calls但对应的ToolMessage已被移除
                    # 替换为不带tool_calls的版本
                    final_msgs.append(AIMessage(content=getattr(msg, 'content', ''), tool_calls=[]))
                else:
                    final_msgs.append(msg)
            cleaned = final_msgs

        state['messages'] = cleaned

        # 调用 graph
        try:
            result = graph.invoke(state, config)
        except Exception as e:
            print(f"[错误] 执行出错: {e}")
            import traceback
            traceback.print_exc()
            test_passed = False
            break

        # 更新状态
        if isinstance(result, dict):
            state = result

        # 提取AI回复
        ai_msg = None
        for msg in reversed(state.get('messages', [])):
            if hasattr(msg, 'type') and msg.type == 'ai':
                ai_msg = msg
                break

        if ai_msg:
            content = getattr(ai_msg, 'content', '') or ''
            if len(content) > 300:
                content = content[:300] + "..."
            if content.strip():
                print(f"[AI回复]: {content}")

            # 检查工具调用
            tool_calls = getattr(ai_msg, 'tool_calls', []) or []
            for tc in tool_calls:
                name = tc.get('name') or (tc.get('function', {}) or {}).get('name')
                if name:
                    print(f"[工具调用]: {name}")
                    if name == 'proceed_to_next_step':
                        args = tc.get('args', {})
                        answers = args.get('step_answers', {})
                        print(f"    step_answers: {str(answers)[:150]}...")

        # 打印状态
        cs = state.get('current_step', '?')
        cc = state.get('case_category', '未设置')
        qual = '有' if get_qualification_from_state(state) else '无'
        print(f"[状态] current_step={cs}, case_category={cc}, qualification={qual}")

        # 记录步骤
        step_results.append({
            'step': current_step,
            'step_name': step_name,
            'has_qualification': bool(get_qualification_from_state(state)),
            'case_category': state.get('case_category'),
        })

    # =========================================================================
    # 测试报告
    # =========================================================================
    print_separator("测试报告")

    print("\n步骤执行摘要:")
    print("-" * 70)
    print(f"{'步骤':<6} {'名称':<20} {'case_category':<15} {'qualification'}")
    print("-" * 70)
    for r in step_results:
        qual_str = "有" if r['has_qualification'] else "无"
        print(f"{r['step']:<6} {r['step_name']:<20} {r['case_category'] or '':<15} {qual_str}")
    print("-" * 70)

    # 验证
    print("\n验证结果:")
    final_qual = get_qualification_from_state(state)
    if final_qual:
        print(f"  [PASS] qualification 不为空")
        cf = final_qual.get('case_facts', '')
        print(f"    - case_facts: {cf[:80]}..." if len(cf) > 80 else f"    - case_facts: {cf}")
        ct = final_qual.get('case_types', [])
        print(f"    - case_types: {ct}")
        rights = final_qual.get('rights_list', [])
        print(f"    - 权益清单 ({len(rights)} 项)")
        test_passed = True
    else:
        print(f"  [FAIL] qualification 为空!")
        # 检查 step_data 中的内容
        step_data = state.get('step_data', {})
        if 'step5_qualification' in step_data:
            print(f"  [INFO] step5_qualification 数据存在但格式不同")
            extra = step_data['step5_qualification'].get('extra', {})
            print(f"  [INFO] extra keys: {list(extra.keys())}")
        test_passed = False

    case_cat = state.get('case_category')
    if case_cat == '欠薪':
        print(f"  [PASS] case_category = '欠薪'")
    else:
        print(f"  [FAIL] case_category = '{case_cat}' (期望: '欠薪')")
        test_passed = False

    print(f"\n最终状态:")
    print(f"  - current_step: {state.get('current_step')}")
    print(f"  - completed_steps: {sorted(state.get('completed_steps', set()))}")
    print(f"  - step_data keys: {list(state.get('step_data', {}).keys())}")
    if 'step5_qualification' in state.get('step_data', {}):
        sq = state['step_data']['step5_qualification']
        print(f"  - step5_qualification status: {sq.get('status')}")
        print(f"  - step5_qualification extra keys: {list(sq.get('extra', {}).keys())}")

    print_separator("测试结论")
    if test_passed:
        print("  [SUCCESS] 所有测试通过!")
    else:
        print("  [FAILED] 测试未完全通过")

    return test_passed


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
