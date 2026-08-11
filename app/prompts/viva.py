"""
Viva section LLM prompts.
Contains prompt builders for generating questions, improving questions, and evaluating viva responses.
"""

from typing import Optional


def build_generate_questions_prompt(
    topic: str, num_questions: int, doc_text: Optional[str] = None
) -> str:
    """
    Build prompt to generate viva questions based on a topic and optional document context.
    """
    context = ""
    if doc_text:
        context = f"\nUse the following document text as context:\n{doc_text}\n"

    return (
        f"Generate {num_questions} viva questions on topic: {topic}. {context}"
        'Respond ONLY with a JSON array: [{"question": "...", "answer": "...", "hint": "..."}, ...]\n'
        "hint can be null."
    )


def build_improve_question_prompt(
    question_text: str, answer_text: str, hint: Optional[str], instruction: str
) -> str:
    """
    Build prompt to refine/improve an existing viva question using user instructions.
    """
    return (
        f"Given this viva question: {question_text}, answer: {answer_text}, hint: {hint}.\n"
        f"User instruction: {instruction}\n"
        'Respond ONLY with JSON: {"question": "...", "answer": "...", "hint": "..."}'
    )


def build_evaluate_answer_prompt(
    question_text: str, correct_answer: str, user_answer: str
) -> str:
    """
    Build prompt to grade candidate's transcribed answer against expected answer.
    """
    return (
        "You are an expert viva examiner. Evaluate the candidate's transcribed answer against the expected correct answer.\n\n"
        f"Question: {question_text}\n"
        f"Expected Correct Answer: {correct_answer}\n"
        f"Candidate's Answer: {user_answer}\n\n"
        "Evaluate the answer out of 10 points (0.0 to 10.0). Be objective but constructive. "
        "Provide a rating (float between 0.0 and 10.0), and detailed feedback explaining your rating.\n"
        "You must respond ONLY with a JSON object in this format:\n"
        "{\n"
        '  "rating": <float between 0.0 and 10.0>,\n'
        '  "feedback": "<string providing clear constructive feedback>"\n'
        "}"
    )
