"""
Practice section LLM prompts.
Contains prompt builders for AI mock practice interview features:
- Initial interview question generation
- Answer evaluation & adaptive routing
- Single topic remark summary
- Overall session evaluation summary
"""

from typing import Dict, List, Optional, Tuple


def build_first_question_system_prompt(difficulty: str = "medium") -> str:
    """
    Build system prompt for formulating the initial mock interview question.
    """
    return (
        "You are an expert technical interviewer. Your goal is to conduct a professional mock interview. "
        "Review the Job Description and Candidate Resume provided. "
        f"Formulate the first technical or situational interview question at the '{difficulty}' difficulty level to kick off the session. "
        "Make it engaging, clear, and relevant to the candidate's profile and the role description. "
        "Provide ONLY the text of the first question. Do not include any greeting, intro, or formatting."
    )


def build_first_question_user_content(
    job_description: Optional[str] = None, resume_text: Optional[str] = None
) -> str:
    """
    Build user content containing Job Description and Candidate Resume context.
    """
    context = ""
    if job_description:
        context += f"\n[Job Description]\n{job_description}\n"
    if resume_text:
        context += f"\n[Candidate Resume]\n{resume_text}\n"
    return f"Context: {context}\nGenerate the first question."


def build_evaluate_and_route_system_prompt(
    followup_count: int, difficulty: str = "medium"
) -> str:
    """
    Build system prompt for the interview decision node (scoring & next route determination).
    """
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

    return (
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


def build_evaluate_and_route_user_content(
    job_description: Optional[str],
    resume_text: Optional[str],
    dialogue_history: List[Dict[str, str]],
    latest_user_answer: str,
) -> str:
    """
    Build user content containing context, conversation history, and latest response.
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

    return (
        f"Context:\n{context}\n"
        f"Dialogue History:\n{history_str}\n"
        f"Latest Candidate Response:\n{latest_user_answer}\n\n"
        "Provide your JSON decision."
    )


def build_question_remark_system_prompt() -> str:
    """
    Build system prompt for generating a consolidated summary report per main question topic.
    """
    return (
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


def build_question_remark_user_content(
    main_question: str, dialogue_thread: List[Dict[str, str]]
) -> str:
    """
    Build user content containing main question and interaction thread.
    """
    thread_str = ""
    for msg in dialogue_thread:
        role_label = "Interviewer" if msg["role"] == "assistant" else "Candidate"
        thread_str += f"{role_label}: {msg['content']}\n"

    return (
        f"Main Question: {main_question}\n"
        f"Interaction Thread:\n{thread_str}\n\n"
        "Provide the JSON evaluation."
    )


def build_overall_summary_system_prompt() -> str:
    """
    Build system prompt for final interview session summary.
    """
    return (
        "You are an senior executive interviewer providing the final comprehensive summary report for a completed mock interview session.\n"
        "Synthesize the candidate's technical performance across all topics along with any provided objective behavioral telemetry.\n"
        "Draft a cohesive, highly professional, encouraging, and constructive final evaluation summary paragraph."
    )


def build_overall_summary_user_content(
    interview_title: str,
    remarks: List[Dict],
    behavioral_summary: Optional[Dict] = None,
) -> str:
    """
    Build user content summarizing topic remarks breakdown and objective behavioral telemetry.
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

    return (
        f"Interview Title: {interview_title}\n\n"
        f"Topic Remarks Breakdown:\n{remarks_summary}\n"
        f"{behavioral_context}\n\n"
        "Provide the final evaluation summary text."
    )
