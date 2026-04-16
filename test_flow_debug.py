# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from langgraph_model.consultation_graph import get_consultation_graph, STEP_NAMES
from langgraph_model.consultation_state import create_initial_state
from langchain_core.messages import HumanMessage

graph = get_consultation_graph()
config = {'configurable': {'thread_id': 'full-flow-v2'}, 'recursion_limit': 80}

state = create_initial_state(session_id='full-flow-v2')
state['messages'] = []

flow = [
    ('AI', 'step1'),
    ('\u7f34\u85aa', 'step2'),
    ('B', 'step2'),
    ('\u5728\u804c', 'step3'),
    ('\u8df3\u8fc7', 'step3'),
    ('\u5df2\u7b7e', 'step3'),
    ('12000', 'step3'),
    ('\u94f6\u884c\u8f6c\u8d26', 'step3'),
    ('\u5168\u90e8\u7eb3\u7eb3', 'step3'),
    ('\u804c\u5458', 'step3'),
    ('2021\u5e743\u6708', 'step3'),
    ('\u52a0\u73ed', 'step3'),
    ('\u7f34\u85aa,\u52a0\u73ed\u8d39', 'step3'),
    ('20000', 'step3'),
    ('\u62ff\u94b1\u8d70\u4eba', 'step3'),
    ('\u8df3\u8fc7', 'step4'),
    ('\u51c6\u786e', 'step5'),
]

for i, (user_input, expected_step) in enumerate(flow):
    print(f"\n=== Round {i+1}: {user_input} -> expect {expected_step} ===")
    state['messages'].append(HumanMessage(content=user_input))

    try:
        result = graph.invoke(state, config=config)
    except Exception as e:
        print(f"ERROR: {e}")
        break

    for k in ['current_step', 'case_category', 'step_data', 'qualification',
               'risk_assessment', 'document_draft', 'roadmap', 'completed_steps', 'evidence_items']:
        if k in result:
            state[k] = result[k]

    msgs = result.get('messages', [])
    ai_msgs = [m for m in msgs if hasattr(m, 'type') and m.type == 'ai']
    if ai_msgs:
        last = ai_msgs[-1]
        content = getattr(last, 'content', '')[:80].replace('\n', ' ')
        print(f"AI: {content}")
        tcs = getattr(last, 'tool_calls', []) or []
        for tc in tcs:
            print(f"  tool: {tc.get('name')}")

    state['messages'] = msgs
    print(f"state: step={state.get('current_step')}, cat={state.get('case_category')}")

    if state.get('current_step', 1) >= 10:
        break

print("\n=== FINAL STATE ===")
print(f"case_category: {state.get('case_category')}")
print(f"current_step: {state.get('current_step')}")
print(f"completed_steps: {sorted(state.get('completed_steps', []))}")
q = state.get('qualification', {})
if q:
    print(f"qualification: case_types={q.get('case_types', [])}")
    print(f"rights_count: {len(q.get('rights_list', []))}")
