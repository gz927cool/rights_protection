"""
Nine-Step Legal Consultation System - Main Skeleton

Phase 1: State and skeleton implementation
Implements 10-step StateGraph + create_agent pattern + handoffs

Architecture:
  Main StateGraph: fixed skeleton, ensures business integrity
  Each step = create_agent: LLM-driven questions + follow-up loops + dynamic stopping
  Handoffs: tools drive cross-step navigation
  dirty_steps: supports backtrack-recalculate protocol
"""
from typing import Annotated, Dict, Literal, Optional, Any
from datetime import datetime
from operator import add as messages_add

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain.tools import tool, ToolRuntime

from langgraph_model.load_cfg import OPENAI_API_KEY, MODEL_NAME, BASE_URL
from langgraph_model.consultation_state import (
    ConsultationState,
    ConsultationInput,
    StepData,
    STEP_NAMES,
    STEP_DISPLAY_NAMES,
    get_dirty_range,
    create_initial_state,
    serialize_state,
    deserialize_state,
)

# LLM model instance
model = ChatOpenAI(
    model=MODEL_NAME,
    api_key=OPENAI_API_KEY,
    base_url=BASE_URL,
    temperature=0,
    max_tokens=4096,
)

# ============================================================================
# Tools: shared across all steps
# ============================================================================

@tool
def go_to_step(runtime: ToolRuntime, step_name: str, reason: str = "") -> str:
    """
    Jump to the specified step and mark the current step as dirty.
    Used when user actively jumps from one step to another (e.g., from step5
    clicks 'return to modify' to step3).
    """
    target_step = STEP_NAMES.index(step_name) + 1
    dirty = get_dirty_range(target_step)
    display = STEP_DISPLAY_NAMES.get(step_name, step_name)
    msg = f"Already jumped to [{display}]."
    if reason:
        msg += f" Reason: {reason}."
    msg += " Subsequent steps marked for update."
    return msg


@tool
def proceed_to_next_step(
    runtime: ToolRuntime,
    step_name: str,
    step_answers: Dict[str, Any],
    extra_data: Optional[Dict[str, Any]] = None,
) -> Command:
    """
    Current step is complete. Carry data to the next step.

    - Update step_data
    - Mark dirty_steps
    - Return Command to parent graph to enter target node
    """
    current_step_num = runtime.state.get("current_step", 1)
    current_step_name = STEP_NAMES[current_step_num - 1]
    target_step_num = current_step_num + 1

    step_data = (runtime.state.get("step_data", {}) or {}).copy()
    step_data[current_step_name] = StepData(
        answers=step_answers,
        status="completed",
        completed_at=datetime.now().isoformat(),
        extra=extra_data or {},
    )

    dirty = get_dirty_range(target_step_num)

    completed = (runtime.state.get("completed_steps", set()) or set()) | {current_step_num}
    existing_dirty = (runtime.state.get("dirty_steps", set()) or set()) | dirty

    return Command(
        goto=STEP_NAMES[target_step_num - 1],
        update={
            "step_data": step_data,
            "current_step": target_step_num,
            "completed_steps": completed,
            "dirty_steps": existing_dirty,
            "last_updated": datetime.now().isoformat(),
        },
        graph=Command.PARENT,
    )


@tool
def request_missing_info(runtime: ToolRuntime, prompt: str) -> str:
    """
    Ask the user for missing information (does not jump steps, stays in current step).
    Agent calls this when it judges that information is insufficient but should
    continue within the current step.
    """
    return prompt


@tool
def back_to_previous_step(
    runtime: ToolRuntime,
    step_name: str,
    reason: str = "",
) -> Command:
    """
    Go back to a specified previous step (e.g., user requests to modify earlier answer).
    Marks from the target step onwards as dirty.
    """
    target_step_num = STEP_NAMES.index(step_name) + 1
    dirty = get_dirty_range(target_step_num)
    existing_dirty = (runtime.state.get("dirty_steps", set()) or set()) | dirty

    return Command(
        goto=step_name,
        update={
            "current_step": target_step_num,
            "dirty_steps": existing_dirty,
            "last_updated": datetime.now().isoformat(),
        },
        graph=Command.PARENT,
    )


@tool
def pause_and_save(runtime: ToolRuntime) -> str:
    """
    Save current progress and return a resume_token.
    User can save progress, close the page, and later restore using the token.
    """
    token = (runtime.state.get("session_id", "") or "") + "_paused"
    return (
        f"Progress saved. Your resume code: [{token}]. "
        "Enter this code next time to continue."
    )


@tool
def check_and_apply_dirty(
    runtime: ToolRuntime,
    action: Literal["recalculate", "keep"],
) -> str:
    """
    When entering a step and a dirty flag is detected, trigger recalculation confirmation.

    If user modified a previous step, dirty_steps will contain this step and all later ones.
    After user confirms:
    - recalculate: clear dirty data and regenerate
    - keep: retain existing dirty data and just clear the flag
    """
    if action == "recalculate":
        return "Dirty data cleared. Will regenerate."
    return "Existing content retained. Continuing."


@tool
def finish_consultation(runtime: ToolRuntime) -> str:
    """User confirms consultation is complete. End the entire flow."""
    return "Thank you for using this legal consultation service. Good luck with your case!"


# ============================================================================
# Step Agent system prompts (Phase 2 will fill these with real prompts)
# ============================================================================

STEP_SYSTEM_PROMPTS: Dict[str, str] = {
    "step1_selector": (
        "You are the reception agent for the Suqian Labor Union legal consultation system. "
        "Introduce users to the two available consultation modes: "
        "1) [Lawyer Video]: connect to a duty lawyer directly (available on working days during service hours); "
        "2) [AI Smart Q&A]: guided conversation through the full consultation process. "
        "Ask the user which mode they prefer and guide them accordingly."
    ),
    "step2_initial": (
        "You are the initial triage agent. "
        "The user has chosen AI Smart Q&A. Guide them to select a problem type: "
        "A) Seek a lawyer video (route to video call); "
        "B) Describe the case freely (user types description, system asks follow-up questions); "
        "C) Interactive Q&A (collect information through guided questions). "
        "Based on the user's choice, guide them to the appropriate path."
    ),
    "step3_common": (
        "You are the general question collector. "
        "Collect all 12 general questions for labor dispute consultation. "
        "All questions use point-and-click / dropdown / calendar input - no manual typing needed. "
        "Questions: "
        "Q1. Current employment status? [Employed / Left / On Leave]; "
        "Q2. Date of leaving? [Calendar + 'Cannot recall']; "
        "Q3. Signed a written labor contract? [Yes / No / Unsure]; "
        "Q4. Approximate monthly salary? [Number input]; "
        "Q5. How is salary paid? [Bank transfer / Cash / WeChat / Alipay]; "
        "Q6. Did the company pay social insurance? [Yes / No / Partial]; "
        "Q7. Job position? [Dropdown: factory worker / food delivery / ride-hailing driver / office / other]; "
        "Q8. Hire date? [Calendar + 'Cannot recall']; "
        "Q9. Weekly working hours? [Standard hours / Overtime / Irregular]; "
        "Q10. What claims are involved? [Multi-select: unpaid wages / overtime pay / compensation / economic compensation / social insurance / other]; "
        "Q11. Approximate amount involved? [Number or 'Unsure']; "
        "Q12. Desired outcome? [Continue working / Leave with payment / Compensation]. "
        "After all 12 questions are completed, proceed to special questions."
    ),
    "step4_special": (
        "You are the special question follow-up agent. "
        "Based on the user's case category (unpaid wages / dismissal / work injury / transfer / social insurance / other), "
        "dynamically load specific questions from the question bank. "
        "After each answer, judge whether core facts are clear: employer name, hire date, labor relationship status, core dispute, and amount involved. "
        "If core facts are clear, call proceed_to_next_step to enter case qualification. "
        "If not clear, continue to the next question. "
        "For multiple case types, sort questions by case type priority."
    ),
    "step5_qualification": (
        "You are the case qualification agent. "
        "Based on all collected information, generate a complete and standardized case fact description. "
        "Determine the cause of action (single or combined), with cause name and three-level code. "
        "Generate a rights list including arbitration claims, compensation amounts, and calculation basis. "
        "User can review and confirm the case description, or return to modify. "
        "Provide a legal basis index button linking to relevant regulations."
    ),
    "step6_evidence": (
        "You are the evidence strategy agent. "
        "Match an evidence checklist specific to the cause of action, divided into 'Required' and 'Supplementary' categories. "
        "Guide the user to mark the status of each evidence item: A=Have / B=Can supplement / C=Cannot obtain. "
        "For B-type evidence, provide acquisition guidance (language templates, operation guides). "
        "Support evidence file upload, stored and categorized by type. "
        "Review uploaded evidence and provide targeted feedback. "
        "Display real-time evidence collection completeness rating: Sufficient / Incomplete / Lacking / Seriously Lacking."
    ),
    "step7_risk": (
        "You are the risk analysis agent. "
        "Comprehensively analyze risks based on case fact clarity, evidence completeness, and possible employer defenses. "
        "Clearly state specific risk points: statute of limitations expiry, broken evidence chain, claim calculation errors, etc. "
        "Highlight high-risk points and provide basic risk mitigation suggestions."
    ),
    "step8_documents": (
        "You are the document generation agent. "
        "Based on case information, evidence list, and rights list, automatically fill document templates. "
        "Support [Arbitration Application] and [Mediation Application]. "
        "Smart validation: highlight fields with unclear facts, pop up supplementary question windows. "
        "User can ask questions about the document content; system modifies or suggests improvements based on the knowledge base. "
        "(Manual editing and export not yet implemented)"
    ),
    "step9_roadmap": (
        "You are the action roadmap planning agent. "
        "Display the three-step rights protection path: Negotiation -> Mediation -> Arbitration. "
        "Each step card shows: detailed guidance, required materials, handling point information, best timing. "
        "For mediation-suitable cases, prompt 'Prioritize union mediation, phone: XXX'. "
        "(Currently using provincial general information; Suqian local data to be added later)"
    ),
    "step10_review": (
        "You are the review consultation agent. "
        "Provide preset prompt templates; user can select or freely input questions for AI review. "
        "Support one-click lawyer assistance: package all collected case data and send to the Suqian Federation of Trade Unions duty lawyer portal. "
        "Users can also click 'Request Lawyer Help' at any step."
    ),
}


# ============================================================================
# Step agents (created from prompts + shared tools)
# ============================================================================

def _make_step_tools(step_name: str):
    return [
        go_to_step,
        proceed_to_next_step,
        request_missing_info,
        back_to_previous_step,
        pause_and_save,
        check_and_apply_dirty,
        finish_consultation,
    ]


def _create_step_agent(step_name: str):
    return create_agent(
        model,
        tools=_make_step_tools(step_name),
        system_prompt=STEP_SYSTEM_PROMPTS.get(step_name, f"Step {step_name}"),
    )


STEP_AGENTS: Dict[str, Any] = {
    name: _create_step_agent(name) for name in STEP_NAMES
}


# ============================================================================
# Build step nodes (LangGraph nodes calling step agents)
# ============================================================================

def _build_step_node(step_name: str):
    def node(state: ConsultationState) -> Dict:
        agent = STEP_AGENTS[step_name]
        result = agent.invoke({
            "messages": state.get("messages", []),
        })
        return result
    return node


# ============================================================================
# Build main StateGraph
# ============================================================================

def create_consultation_graph():
    """
    Create the main StateGraph for the nine-step consultation system.

    Skeleton: START -> step1 -> step2 -> ... -> step10 -> END
    Each node internally uses create_agent; cross-node jumping is done via
    tools using Command(goto=..., graph=Command.PARENT).
    """
    workflow = StateGraph(
        ConsultationState,
        input_schema=ConsultationInput,
    )

    # Add all step nodes
    for step_name in STEP_NAMES:
        workflow.add_node(step_name, _build_step_node(step_name))

    # Entry and exit
    workflow.add_edge(START, STEP_NAMES[0])
    workflow.add_edge(STEP_NAMES[-1], END)

    checkpointer = InMemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# ============================================================================
# Graph instance (singleton)
# ============================================================================

_graph_instance: Optional[Any] = None


def get_consultation_graph() -> Any:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = create_consultation_graph()
    return _graph_instance


# ============================================================================
# Convenience entry point
# ============================================================================

def start_consultation(
    session_id: str,
    member_id: Optional[str] = None,
    resume_token: Optional[str] = None,
) -> Dict:
    if resume_token:
        return create_initial_state(session_id, member_id)
    return create_initial_state(session_id, member_id)


# ============================================================================
# Debug entry
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Nine-Step Consultation System - Skeleton Test")
    print("=" * 60)

    initial = create_initial_state(
        session_id="test-session-001",
        member_id="member-001",
    )
    print(f"\nInitial state:")
    print(f"  current_step: {initial['current_step']}")
    print(f"  session_id: {initial['session_id']}")
    print(f"  dirty_steps: {initial['dirty_steps']}")

    serialized = serialize_state(initial)
    print(f"\nSerialization OK, length: {len(serialized)}")

    restored = deserialize_state(serialized)
    print(f"Deserialization OK: session_id={restored['session_id']}")

    graph = get_consultation_graph()
    print(f"\nGraph created: {graph}")
    print(f"Nodes: {list(graph.nodes.keys())}")

    config = {
        "configurable": {"thread_id": "test-run-001"},
        "recursion_limit": 100,
    }

    test_state = create_initial_state("test-run-001")
    test_messages = [HumanMessage(content="I want to consult about labor dispute, I was fired by the company")]

    print("\n" + "=" * 60)
    print("Simulating Step 1: Mode Selection")
    print("=" * 60)
    print(f"User says: {test_messages[0].content}")

    step_count = 0
    for event in graph.stream(
        {"messages": test_messages, "session_id": "test-run-001"},
        config=config,
    ):
        step_count += 1
        if isinstance(event, dict):
            for node_name, node_output in event.items():
                msgs = node_output.get("messages", [])
                if msgs:
                    last_msg = msgs[-1]
                    if hasattr(last_msg, "content") and last_msg.content:
                        preview = last_msg.content[:200].replace("\n", " ")
                        print(f"\n[{node_name}] reply: {preview}...")
        print("---")

    print(f"\nTotal steps executed: {step_count}")
    print("\nSkeleton test complete")
