from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class InterviewState(TypedDict, total=False):
    """
    State schema for a single persistent AI interview session thread.
    Message history is automatically appended and preserved by LangGraph using `add_messages`.
    """
    # Conversation Memory
    messages: Annotated[List[BaseMessage], add_messages]

    # Session Metadata
    session_id: str
    job_description: Optional[str]
    resume_text: Optional[str]
    difficulty: str  # "easy" | "medium" | "hard"
    max_topics: int  # Max technical main question topics (default: 5)

    # State Counters & Progress
    topic_count: int
    followup_count: int
    current_question: str

    # Evaluation Output & Tracking
    evaluations: List[Dict[str, Any]]
    last_decision: str  # "followup" | "next_question" | "end_interview"
    last_rating: Optional[float]
    last_feedback: Optional[str]
    session_status: str  # "active" | "completed"
    final_report: Optional[Dict[str, Any]]
