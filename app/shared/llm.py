import json
import logging
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from groq import AsyncGroq

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize client
client = AsyncGroq(api_key=settings.GROQ_API_KEY)


async def generate_questions(
    topic: str, num_questions: int, doc_text: Optional[str] = None
) -> List[Dict]:
    context = ""
    if doc_text:
        context = f"\nUse the following document text as context:\n{doc_text}\n"

    prompt = (
        f"Generate {num_questions} viva questions on topic: {topic}. {context}"
        'Respond ONLY with a JSON array: [{"question": "...", "answer": "...", "hint": "..."}, ...]\n'
        "hint can be null."
    )

    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        response_text = chat_completion.choices[0].message.content
        # Strip code block backticks if present
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        data = json.loads(response_text)
        if not isinstance(data, list):
            raise TypeError("Expected a list of questions")
        return data
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(
            f"Failed to parse LLM response as JSON: {e}. Response was: {response_text if 'response_text' in locals() else 'None'}"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse valid JSON response from the LLM",
        )
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with LLM service: {str(e)}",
        )


async def improve_question(
    question_text: str, answer_text: str, hint: Optional[str], instruction: str
) -> Dict:
    prompt = (
        f"Given this viva question: {question_text}, answer: {answer_text}, hint: {hint}.\n"
        f"User instruction: {instruction}\n"
        'Respond ONLY with JSON: {"question": "...", "answer": "...", "hint": "..."}'
    )

    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        response_text = chat_completion.choices[0].message.content
        # Strip code block backticks if present
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        data = json.loads(response_text)
        if not isinstance(data, dict):
            raise TypeError("Expected a dictionary response")
        return data
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(
            f"Failed to parse LLM response as JSON: {e}. Response was: {response_text if 'response_text' in locals() else 'None'}"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse valid JSON response from the LLM",
        )
    except Exception as e:
        logger.error(f"Error calling LLM: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with LLM service: {str(e)}",
        )
