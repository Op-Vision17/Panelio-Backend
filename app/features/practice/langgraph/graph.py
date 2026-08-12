import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.features.practice.langgraph.nodes import (
    ask_followup_question_node,
    ask_initial_question_node,
    ask_next_topic_question_node,
    evaluate_and_route_node,
    generate_summary_node,
)
from app.features.practice.langgraph.state import InterviewState

logger = logging.getLogger(__name__)


def entry_router(state: InterviewState) -> str:
    """
    Decides whether this invocation is starting a new session
    or continuing an existing candidate thread.
    """
    if state.get("session_status") == "completed":
        return "generate_summary"

    # If initial question hasn't been asked yet
    if not state.get("current_question") or state.get("topic_count", 0) == 0:
        return "ask_initial_question"

    # Candidate has submitted an answer -> Evaluate & Route
    return "evaluate_and_route"


def route_next_step(state: InterviewState) -> str:
    """
    Conditional router after answer evaluation.
    """
    last_decision = state.get("last_decision", "next_question")
    topic_count = state.get("topic_count", 1)
    followup_count = state.get("followup_count", 0)
    max_topics = state.get("max_topics", 5)

    if last_decision == "followup" and followup_count < 2:
        return "ask_followup_question"
    elif last_decision == "next_question" and topic_count < max_topics:
        return "ask_next_topic_question"
    else:
        return "generate_summary"


# Shared in-memory checkpointer instance
memory_checkpointer = MemorySaver()


def build_interview_graph(checkpointer=None):
    """
    Builds and compiles the LangGraph Interview StateGraph.
    """
    if checkpointer is None:
        checkpointer = memory_checkpointer

    builder = StateGraph(InterviewState)

    # Register Nodes
    builder.add_node("ask_initial_question", ask_initial_question_node)
    builder.add_node("evaluate_and_route", evaluate_and_route_node)
    builder.add_node("ask_followup_question", ask_followup_question_node)
    builder.add_node("ask_next_topic_question", ask_next_topic_question_node)
    builder.add_node("generate_summary", generate_summary_node)

    # Entry point conditional routing
    builder.add_conditional_edges(
        START,
        entry_router,
        {
            "ask_initial_question": "ask_initial_question",
            "evaluate_and_route": "evaluate_and_route",
            "generate_summary": "generate_summary",
        },
    )

    # After initial question, pause turn for candidate response
    builder.add_edge("ask_initial_question", END)

    # After evaluation, conditionally route to next question or summary
    builder.add_conditional_edges(
        "evaluate_and_route",
        route_next_step,
        {
            "ask_followup_question": "ask_followup_question",
            "ask_next_topic_question": "ask_next_topic_question",
            "generate_summary": "generate_summary",
        },
    )

    builder.add_edge("ask_followup_question", END)
    builder.add_edge("ask_next_topic_question", END)
    builder.add_edge("generate_summary", END)

    return builder.compile(checkpointer=checkpointer)


# Compiled global graph instance
interview_graph = build_interview_graph()


async def initialize_session_thread(
    session_id: str,
    job_description: Optional[str] = None,
    resume_text: Optional[str] = None,
    difficulty: str = "medium",
    max_topics: int = 5,
) -> Dict[str, Any]:
    """
    Initializes a new interview thread under thread_id = session_id in LangGraph.
    """
    config = {"configurable": {"thread_id": str(session_id)}}

    initial_state = {
        "session_id": str(session_id),
        "job_description": job_description,
        "resume_text": resume_text,
        "difficulty": difficulty,
        "max_topics": max_topics,
        "topic_count": 0,
        "followup_count": 0,
        "session_status": "active",
        "evaluations": [],
    }

    result = await interview_graph.ainvoke(initial_state, config=config)
    return result


async def submit_candidate_answer_thread(
    session_id: str, candidate_text: str
) -> Dict[str, Any]:
    """
    Appends candidate answer to the thread_id state and executes evaluation + routing.
    """
    config = {"configurable": {"thread_id": str(session_id)}}

    # Append HumanMessage answer into graph thread memory and trigger graph
    input_update = {"messages": [HumanMessage(content=candidate_text)]}
    result = await interview_graph.ainvoke(input_update, config=config)

    return result
