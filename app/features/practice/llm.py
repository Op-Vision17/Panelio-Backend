import json
import logging
from typing import Dict, List, Optional

from app.prompts.practice import (
    build_evaluate_and_route_system_prompt,
    build_evaluate_and_route_user_content,
    build_first_question_system_prompt,
    build_first_question_user_content,
    build_overall_summary_system_prompt,
    build_overall_summary_user_content,
    build_question_remark_system_prompt,
    build_question_remark_user_content,
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


async def generate_first_question(
    job_description: Optional[str] = None,
    resume_text: Optional[str] = None,
    difficulty: str = "medium"
) -> str:
    """
    Generate the first interview question based on the JD and Resume.
    """
    system_prompt = build_first_question_system_prompt(difficulty=difficulty)
    user_content = build_first_question_user_content(
        job_description=job_description, resume_text=resume_text
    )

    try:
        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=MODEL_NAME,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating first question: {e}")
        return "Could you please introduce yourself and walk me through your most relevant professional experience?"


async def evaluate_response_and_route(
    job_description: Optional[str],
    resume_text: Optional[str],
    dialogue_history: List[Dict[str, str]],
    latest_user_answer: str,
    followup_count: int,
    difficulty: str = "medium"
) -> Dict:
    """
    Deciding Node: Evaluates candidate's response, rates it, gives feedback, and decides the next route.
    Returns:
    {
      "rating": float,
      "feedback": str,
      "decision": "followup" | "next_question" | "end_interview",
      "reason": str,
      "next_question_text": str
    }
    """
    system_prompt = build_evaluate_and_route_system_prompt(
        followup_count=followup_count, difficulty=difficulty
    )
    user_content = build_evaluate_and_route_user_content(
        job_description=job_description,
        resume_text=resume_text,
        dialogue_history=dialogue_history,
        latest_user_answer=latest_user_answer,
    )

    try:
        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=MODEL_NAME,
            response_format={"type": "json_object"}
        )
        response_text = _clean_json_response(completion.choices[0].message.content)
        data = json.loads(response_text)
        
        # Hard constraint enforcement in python logic
        if followup_count >= 2 and data.get("decision") == "followup":
            data["decision"] = "next_question"
            # If the LLM generated a followup, we ask it to be a new main question instead or default it
            logger.info("Overrode LLM followup decision due to limit of 2 followups.")
            
        return data
    except Exception as e:
        logger.error(f"Error in evaluate_response_and_route: {e}")
        # Return fallback values
        return {
            "rating": 5.0,
            "feedback": "Answer recorded.",
            "decision": "next_question" if followup_count >= 2 else "followup",
            "reason": "Fallback due to LLM timeout/error.",
            "next_question_text": "Thank you for the answer. Let's move to the next question. What are your key strengths in system design?"
        }


async def generate_question_remark(
    main_question: str,
    dialogue_thread: List[Dict[str, str]]
) -> Dict:
    """
    Generate a single consolidated remark/rating for a completed main question and its follow-ups.
    Returns:
    {
      "rating": float,
      "feedback": str
    }
    """
    system_prompt = build_question_remark_system_prompt()
    user_content = build_question_remark_user_content(
        main_question=main_question, dialogue_thread=dialogue_thread
    )

    try:
        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=MODEL_NAME,
            response_format={"type": "json_object"}
        )
        response_text = _clean_json_response(completion.choices[0].message.content)
        return json.loads(response_text)
    except Exception as e:
        logger.error(f"Error in generate_question_remark: {e}")
        return {
            "rating": 5.0,
            "feedback": "Answer thread evaluated with generic feedback."
        }


async def generate_overall_session_summary(
    interview_title: str,
    remarks: List[Dict],
    behavioral_summary: Optional[Dict] = None
) -> str:
    """
    Generates a comprehensive final interview evaluation summary incorporating
    technical performance remarks and objective behavioral analysis metrics.
    """
    system_prompt = build_overall_summary_system_prompt()
    user_content = build_overall_summary_user_content(
        interview_title=interview_title,
        remarks=remarks,
        behavioral_summary=behavioral_summary,
    )

    try:
        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model=MODEL_NAME,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating overall session summary: {e}")
        return f"Successfully completed mock interview on {interview_title}."

