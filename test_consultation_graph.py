"""
九步咨询骨架测试

测试九步 StateGraph 的核心机制：
1. 状态创建与序列化
2. 脏标记范围计算
3. 步骤名称映射
4. Graph 节点结构
5. 流式输出格式

（不包含需要真实 LLM 调用的端到端测试）
"""
import sys
sys.path.insert(0, ".")

from langgraph_model.consultation_state import (
    ConsultationState,
    create_initial_state,
    serialize_state,
    deserialize_state,
    STEP_NAMES,
    STEP_DISPLAY_NAMES,
    get_dirty_range,
    get_step_name,
    get_step_number,
)


def test_create_initial_state():
    state = create_initial_state("session-001", "member-001")
    assert state["current_step"] == 1
    assert state["session_id"] == "session-001"
    assert state["member_id"] == "member-001"
    assert state["completed_steps"] == set()
    assert state["dirty_steps"] == set()
    assert state["case_category"] is None
    assert state["case_types"] == []
    assert state["evidence_items"] == []
    assert state["evidence_files"] == {}
    print("  create_initial_state: PASS")


def test_serialization_roundtrip():
    state = create_initial_state("session-001")
    serialized = serialize_state(state)
    restored = deserialize_state(serialized)
    assert restored["session_id"] == "session-001"
    assert restored["current_step"] == 1
    assert isinstance(restored["dirty_steps"], set)
    print("  serialization_roundtrip: PASS")


def test_dirty_range():
    # 从第3步dirty，应影响3-10步
    assert get_dirty_range(3) == {3, 4, 5, 6, 7, 8, 9, 10}
    # 从第5步dirty，应影响5-10步
    assert get_dirty_range(5) == {5, 6, 7, 8, 9, 10}
    # 从第1步dirty，应影响1-10步
    assert get_dirty_range(1) == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
    print("  dirty_range: PASS")


def test_step_mapping():
    assert len(STEP_NAMES) == 10
    assert STEP_NAMES[0] == "step1_selector"
    assert STEP_NAMES[9] == "step10_review"
    assert get_step_name(1) == "step1_selector"
    assert get_step_name(10) == "step10_review"
    assert get_step_number("step1_selector") == 1
    assert get_step_number("step10_review") == 10
    print("  step_mapping: PASS")


def test_step_display_names():
    assert STEP_DISPLAY_NAMES["step1_selector"] == "\u6a21\u5f0f\u9009\u62e9"
    assert STEP_DISPLAY_NAMES["step10_review"] == "\u6c42\u52a9\u590d\u6838"
    print("  step_display_names: PASS")


def test_graph_structure():
    from langgraph_model.consultation_graph import get_consultation_graph

    graph = get_consultation_graph()
    node_names = list(graph.nodes.keys())

    # Graph should have: __start__, 10 step nodes, __end__
    assert "__start__" in node_names
    # END is a LangGraph special constant, not a regular node
    for step_name in STEP_NAMES:
        assert step_name in node_names, f"{step_name} not in graph nodes"

    assert len(STEP_NAMES) == 10
    print("  graph_structure: PASS")


def test_graph_stream_single_step():
    """测试单步流式输出格式（不走 LLM，只验证 stream 返回结构）"""
    from langgraph_model.consultation_graph import get_consultation_graph
    from langchain_core.messages import HumanMessage

    graph = get_consultation_graph()
    config = {
        "configurable": {"thread_id": "test-stream-001"},
        "recursion_limit": 100,
    }

    # 用假消息触发 step1（不走 LLM 直接测试 stream 格式）
    events = list(graph.stream(
        {"messages": [HumanMessage(content="test")], "session_id": "test-stream-001"},
        config=config,
    ))

    assert len(events) >= 1
    assert isinstance(events[0], dict)
    # 每个 event 的 key 应该是节点名
    for event in events:
        for key in event.keys():
            assert key in STEP_NAMES or key in ["__start__", "__end__"]
    print("  graph_stream_single_step: PASS")


if __name__ == "__main__":
    print("=" * 60)
    print("Nine-Step Skeleton Tests")
    print("=" * 60)

    test_create_initial_state()
    test_serialization_roundtrip()
    test_dirty_range()
    test_step_mapping()
    test_step_display_names()
    test_graph_structure()
    test_graph_stream_single_step()

    print()
    print("All tests PASSED")
