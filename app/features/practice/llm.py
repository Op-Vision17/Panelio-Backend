import json
import logging
from typing import Dict, List, Optional

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
    context = ""
    if job_description:
        context += f"\n[Job Description]\n{job_description}\n"
    if resume_text:
        context += f"\n[Candidate Resume]\n{resume_text}\n"

    system_prompt = (
        "You are an expert technical interviewer. Your goal is to conduct a professional mock interview. "
        "Review the Job Description and Candidate Resume provided. "
        f"Formulate the first technical or situational interview question at the '{difficulty}' difficulty level to kick off the session. "
        "Make it engaging, clear, and relevant to the candidate's profile and the role description."
        "Provide ONLY the text of the first question. Do not include any greeting, intro, or formatting."
    )

    try:
        completion = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {context}\nGenerate the first question."}
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
    context = ""
    if job_description:
        context += f"\n[Job Description]\n{job_description}\n"
    if resume_text:
        context += f"\n[Candidate Resume]\n{resume_text}\n"

    history_str = ""
    for msg in dialogue_history:
        role_label = "Interviewer" if msg["role"] == "assistant" else "Candidate"
        history_str += f"{role_label}: {msg['content']}\n"

    # Enforce maximum 2 follow-ups
    constraints = ""
    if followup_count >= 2:
        constraints = (
            "CRITICAL: We have already asked 2 follow-ups on this topic. "
            "You MUST set the decision to 'next_question' or 'end_interview'. Do NOT decide 'followup'."
        )
    else:
        constraints = (
            "You can choose 'followup' if the candidate's answer is brief, incomplete, or contains interesting claims "
            "that warrant deeper technical digging (Max 2 follow-ups per topic). "
            "Otherwise, choose 'next_question' to pivot to a new technical area."
        )

    system_prompt = (
        "You are the central decision node and evaluator for an interactive mock interview. "
        "Assess the candidate's latest response against the question asked, context (JD and Resume), and history.\n\n"
        f"The target difficulty level of the interview is '{difficulty}'. "
        "Formulate any follow-up or new question to match this technical depth.\n\n"
        "Evaluate the latest response out of 10.0 points. Provide objective, constructive feedback.\n"
        "Then, decide the next action:\n"
        "1. 'followup': Ask a follow-up question digging deeper into their response.\n"
        "2. 'next_question': Move to a brand-new main technical/situational question.\n"
        "3. 'end_interview': If 5 main question topics have been covered, end the interview.\n\n"
        f"{constraints}\n\n"
        "You must respond ONLY with a JSON object in this exact schema:\n"
        "{\n"
        '  "rating": <float, 0.0 to 10.0>,\n'
        '  "feedback": "<detailed feedback string>",\n'
        '  "decision": "followup" | "next_question" | "end_interview",\n'
        '  "reason": "<reasoning for this decision>",\n'
        '  "next_question_text": "<text of follow-up or new question, empty string if ending>"\n'
        "}"
    )

    user_content = (
        f"Context:\n{context}\n"
        f"Dialogue History:\n{history_str}\n"
        f"Latest Candidate Response:\n{latest_user_answer}\n\n"
        "Provide your JSON decision."
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
    thread_str = ""
    for msg in dialogue_thread:
        role_label = "Interviewer" if msg["role"] == "assistant" else "Candidate"
        thread_str += f"{role_label}: {msg['content']}\n"

    system_prompt = (
        "You are an senior interviewer drafting a consolidated summary report for a candidate's response to an interview topic.\n"
        "Review the entire discussion thread starting with the main question, along with any subsequent follow-up interactions.\n"
        "Provide a single consolidated grade rating (0.0 to 10.0) representing the candidate's command over this specific topic, "
        "and a detailed, constructive feedback paragraph summarizing their performance on this topic.\n\n"
        "You must respond ONLY with a JSON object in this exact schema:\n"
        "{\n"
        '  "rating": <float, 0.0 to 10.0>,\n'
        '  "feedback": "<consolidated constructive summary feedback string>"\n'
        "}"
    )

    user_content = (
        f"Main Question: {main_question}\n"
        f"Interaction Thread:\n{thread_str}\n\n"
        "Provide the JSON evaluation."
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
    remarks_summary = ""
    for idx, r in enumerate(remarks, 1):
        q_text = r.get("question_text") if isinstance(r, dict) else getattr(r, "question_text", "")
        rating = r.get("rating") if isinstance(r, dict) else getattr(r, "rating", 0.0)
        feedback = r.get("feedback") if isinstance(r, dict) else getattr(r, "feedback", "")
        remarks_summary += f"Topic {idx}: {q_text}\nGrade: {rating}/10.0\nFeedback: {feedback}\n\n"

    behavioral_context = ""
    if behavioral_summary and behavioral_summary.get("total_frames_analyzed", 0) > 0:
        face_vis = behavioral_summary.get("face_visibility_pct", 0.0)
        eye_contact = behavioral_summary.get("eye_contact_pct", 0.0)
        looking_away_events = behavioral_summary.get("looking_away_events", 0)
        avg_look_away_dur = behavioral_summary.get("avg_looking_away_duration_sec", 0.0)
        posture_upright = behavioral_summary.get("posture_summary", {}).get("upright_pct", 0.0)

        behavioral_context = (
            "\n[Objective Behavioral Telemetry Metrics]\n"
            f"- Face Visibility in Frame: {face_vis}%\n"
            f"- Direct Eye Contact / Camera Engagement Duration: {eye_contact}%\n"
            f"- Sustained Looking Away Events (>2s): {looking_away_events} (Avg Duration: {avg_look_away_dur}s)\n"
            f"- Posture Alignment: {posture_upright}% Upright\n\n"
            "STRICT GUIDELINE FOR BEHAVIORAL FEEDBACK:\n"
            "Incorporate these empirical metrics constructively into your evaluation summary (e.g., noting strong camera engagement or suggesting keeping eye level steady).\n"
            "DO NOT make subjective assumptions or emotional judgements such as claiming the candidate was 'nervous', 'anxious', 'lacking confidence', or 'deceptive'. Focus strictly on objective visual engagement observations."
        )

    system_prompt = (
        "You are an senior executive interviewer providing the final comprehensive summary report for a completed mock interview session.\n"
        "Synthesize the candidate's technical performance across all topics along with any provided objective behavioral telemetry.\n"
        "Draft a cohesive, highly professional, encouraging, and constructive final evaluation summary paragraph."
    )

    user_content = (
        f"Interview Title: {interview_title}\n\n"
        f"Topic Remarks Breakdown:\n{remarks_summary}\n"
        f"{behavioral_context}\n\n"
        "Provide the final evaluation summary text."
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
