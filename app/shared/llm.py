import json
import logging
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from groq import AsyncGroq

from app.core.config import settings
from app.prompts.viva import (
    build_evaluate_answer_prompt,
    build_generate_questions_prompt,
    build_improve_question_prompt,
)

logger = logging.getLogger(__name__)

# Initialize client
client = AsyncGroq(api_key=settings.GROQ_API_KEY)


async def generate_questions(
    topic: str, num_questions: int, doc_text: Optional[str] = None
) -> List[Dict]:
    prompt = build_generate_questions_prompt(
        topic=topic, num_questions=num_questions, doc_text=doc_text
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
    prompt = build_improve_question_prompt(
        question_text=question_text,
        answer_text=answer_text,
        hint=hint,
        instruction=instruction,
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


async def evaluate_answer(
    question_text: str, correct_answer: str, user_answer: str
) -> Dict:
    prompt = build_evaluate_answer_prompt(
        question_text=question_text,
        correct_answer=correct_answer,
        user_answer=user_answer,
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

        rating = data.get("rating")
        feedback = data.get("feedback")

        if rating is None or feedback is None:
            raise KeyError("Missing required keys in LLM response")

        try:
            data["rating"] = float(rating)
        except (ValueError, TypeError):
            data["rating"] = 0.0

        return data
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.error(
            f"Failed to parse LLM response as JSON: {e}. Response was: {response_text if 'response_text' in locals() else 'None'}"
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse valid JSON response from the LLM",
        )
    except Exception as e:
        logger.error(f"Error calling LLM for evaluation: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error communicating with LLM service: {str(e)}",
        )
