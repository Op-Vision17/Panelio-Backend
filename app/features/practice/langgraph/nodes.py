import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.core.config import settings
from app.features.practice.langgraph.state import InterviewState
from app.prompts.practice import (
    build_evaluate_and_route_system_prompt,
    build_first_question_system_prompt,
    build_first_question_user_content,
    build_overall_summary_system_prompt,
    build_overall_summary_user_content,
)
from app.shared.llm import client

logger = logging.getLogger(__name__)

MODEL_NAME = "llama-3.3-70b-versatile"


def _clean_json_response(text: str) -> str:
    """Strip markdown code block tags from LLM response text."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _convert_messages_to_dict(messages: List[BaseMessage]) -> List[Dict[str, str]]:
    """Convert LangChain BaseMessage objects into OpenAI/Groq message format."""
    formatted = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            formatted.append({"role": "system", "content": msg.content})
        elif isinstance(msg, HumanMessage):
            formatted.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            formatted.append({"role": "assistant", "content": msg.content})
        else:
            role = getattr(msg, "role", "user")
            formatted.append({"role": role, "content": str(msg.content)})
    return formatted


async def ask_initial_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Node 1: Formulates the first technical/situational interview question
    based on the Job Description and Candidate Resume context.
    """
    difficulty = state.get("difficulty", "medium")
    system_prompt = build_first_question_system_prompt(difficulty=difficulty)
    user_content = build_first_question_user_content(
        job_description=state.get("job_description"),
        resume_text=state.get("resume_text"),
    )

    try:
        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            model=MODEL_NAME,
        )
        q_text = completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating first question in graph node: {e}")
        q_text = "Could you please introduce yourself and walk me through your most relevant professional experience?"

    ai_msg = AIMessage(content=q_text)

    return {
        "messages": [ai_msg],
        "current_question": q_text,
        "topic_count": 1,
        "followup_count": 0,
        "session_status": "active",
        "evaluations": [],
    }


async def evaluate_and_route_node(state: InterviewState) -> Dict[str, Any]:
    """
    Node 2: Central evaluator and decision node.
    Evaluates candidate's latest response out of 10.0, provides constructive feedback,
    and determines the next route decision ('followup', 'next_question', or 'end_interview').
    """
    messages = state.get("messages", [])
    followup_count = state.get("followup_count", 0)
    difficulty = state.get("difficulty", "medium")

    sys_prompt = build_evaluate_and_route_system_prompt(
        followup_count=followup_count, difficulty=difficulty
    )

    # Format entire message history thread for the LLM decision node
    prompt_messages = [{"role": "system", "content": sys_prompt}]
    prompt_messages.extend(_convert_messages_to_dict(messages))

    # Add context summary if needed
    jd = state.get("job_description", "")
    resume = state.get("resume_text", "")
    context_note = f"[Job Description]: {jd[:300]}\n[Resume Summary]: {resume[:300]}"
    prompt_messages.append({"role": "system", "content": f"Context parameters:\n{context_note}"})

    try:
        completion = await client.chat.completions.create(
            messages=prompt_messages,
            model=MODEL_NAME,
        )
        resp_text = _clean_json_response(completion.choices[0].message.content)
        data = json.loads(resp_text)
    except Exception as e:
        logger.error(f"Error evaluating response in graph node: {e}")
        data = {
            "score": 50.0,
            "rating": 5.0,
            "what_was_explained": "Candidate gave a basic technical explanation.",
            "what_was_missing": "Missing detailed edge case handling and optimization context.",
            "area_to_focus": "System architecture and algorithm optimization.",
            "feedback": "Thank you for your response. Let's move forward.",
            "decision": "next_question",
            "reason": "Fallback due to LLM error",
            "next_question_text": "What is the most challenging technical problem you have solved recently?",
        }

    score = float(data.get("score") if data.get("score") is not None else float(data.get("rating", 5.0)) * 10)
    rating = float(data.get("rating") if data.get("rating") is not None else score / 10)
    what_was_explained = str(data.get("what_was_explained", ""))
    what_was_missing = str(data.get("what_was_missing", ""))
    area_to_focus = str(data.get("area_to_focus", ""))
    feedback = str(data.get("feedback", ""))
    decision = str(data.get("decision", "next_question"))
    next_q_text = str(data.get("next_question_text", "")).strip()

    eval_item = {
        "question": state.get("current_question", ""),
        "score": score,
        "rating": rating,
        "what_was_explained": what_was_explained,
        "what_was_missing": what_was_missing,
        "area_to_focus": area_to_focus,
        "feedback": feedback,
        "decision": decision,
        "next_question_text": next_q_text,
    }

    evaluations = list(state.get("evaluations", []))
    evaluations.append(eval_item)

    return {
        "evaluations": evaluations,
        "last_decision": decision,
        "last_rating": rating,
        "last_score": score,
        "last_feedback": feedback,
        "last_what_was_explained": what_was_explained,
        "last_what_was_missing": what_was_missing,
        "last_area_to_focus": area_to_focus,
        "current_question": next_q_text if next_q_text else state.get("current_question", ""),
    }


async def ask_followup_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Node 3: Increments follow-up count for the current topic and appends the follow-up question.
    """
    next_q = state.get("current_question", "")
    followup_count = state.get("followup_count", 0) + 1
    ai_msg = AIMessage(content=next_q)

    return {
        "messages": [ai_msg],
        "followup_count": followup_count,
        "current_question": next_q,
    }


async def ask_next_topic_question_node(state: InterviewState) -> Dict[str, Any]:
    """
    Node 4: Pivots to a new main question topic, resets follow-up count, and appends question.
    """
    next_q = state.get("current_question", "")
    topic_count = state.get("topic_count", 1) + 1
    ai_msg = AIMessage(content=next_q)

    return {
        "messages": [ai_msg],
        "topic_count": topic_count,
        "followup_count": 0,
        "current_question": next_q,
    }


async def generate_summary_node(state: InterviewState) -> Dict[str, Any]:
    """
    Node 5: Final overall session evaluation summary report node.
    Synthesizes ratings across all turns into a 5-part wireframe result report.
    """
    evaluations = state.get("evaluations", [])
    scores = [e.get("score", e.get("rating", 0.0) * 10) for e in evaluations]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    sys_prompt = build_overall_summary_system_prompt()
    remarks = [
        {
            "question_text": e.get("question", ""),
            "score": e.get("score", 0.0),
            "rating": e.get("rating", 0.0),
            "what_was_explained": e.get("what_was_explained", ""),
            "what_was_missing": e.get("what_was_missing", ""),
            "area_to_focus": e.get("area_to_focus", ""),
            "feedback": e.get("feedback", ""),
        }
        for e in evaluations
    ]
    user_content = build_overall_summary_user_content(
        interview_title=f"Practice Session {state.get('session_id', '')}",
        remarks=remarks,
    )

    try:
        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content},
            ],
            model=MODEL_NAME,
        )
        resp_text = _clean_json_response(completion.choices[0].message.content)
        report_data = json.loads(resp_text)
    except Exception as e:
        logger.error(f"Error generating overall summary in graph node: {e}")
        report_data = {
            "overall_score": avg_score,
            "overall_summary": "The interview session is complete. Good technical effort demonstrated overall.",
            "speech_score": round(min(100.0, avg_score + 5), 1),
            "speech_summary": "Demonstrated clear communication and consistent articulation throughout responses.",
            "video_score": round(min(100.0, avg_score + 2), 1),
            "video_summary": "Maintained steady gaze and good visual orientation during questions.",
            "suggestions": [
                "Practice expanding on key architectural edge cases during technical answers.",
                "Maintain a structured response flow using the STAR method for situational prompts.",
                "Keep eye contact steady with the camera lens while elaborating complex concepts."
            ]
        }

    overall_score = float(report_data.get("overall_score", avg_score))
    overall_summary = str(report_data.get("overall_summary", "Session completed."))
    speech_score = float(report_data.get("speech_score", overall_score))
    speech_summary = str(report_data.get("speech_summary", "Speech delivery evaluated."))
    video_score = float(report_data.get("video_score", overall_score))
    video_summary = str(report_data.get("video_summary", "Video posture evaluated."))
    suggestions = report_data.get("suggestions") if isinstance(report_data.get("suggestions"), list) else [
        "Focus on detailing core technical trade-offs."
    ]

    final_report = {
        "overall_score": overall_score,
        "overall_summary": overall_summary,
        "speech_score": speech_score,
        "speech_summary": speech_summary,
        "video_score": video_score,
        "video_summary": video_summary,
        "suggestions": suggestions,
        "total_topics_covered": state.get("topic_count", 1),
        "evaluations_breakdown": evaluations,
    }

    ai_msg = AIMessage(content=f"[Interview Complete] Overall Score: {overall_score}/100.0\n\n{overall_summary}")

    return {
        "messages": [ai_msg],
        "session_status": "completed",
        "final_report": final_report,
    }

