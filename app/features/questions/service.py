import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.questions.dao import QuestionDAO
from app.features.questions.model import Question
from app.features.questions.schema import (
    QuestionImproveRequest,
    QuestionUpdate,
)
from app.shared.llm import improve_question as llm_improve_question


async def update_question(
    db: AsyncSession, question_id: uuid.UUID, user_id: uuid.UUID, data: QuestionUpdate
) -> Question:
    q_dao = QuestionDAO(db)
    question = await q_dao.get_by_id_with_viva(question_id)

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )
    if question.viva.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(question, key, value)

    return await q_dao.update(question)


async def delete_question(db: AsyncSession, question_id: uuid.UUID, user_id: uuid.UUID):
    q_dao = QuestionDAO(db)
    question = await q_dao.get_by_id_with_viva(question_id)

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )
    if question.viva.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    await q_dao.delete(question)



async def improve_existing_question(
    db: AsyncSession,
    question_id: uuid.UUID,
    user_id: uuid.UUID,
    data: QuestionImproveRequest,
) -> dict:
    q_dao = QuestionDAO(db)
    question = await q_dao.get_by_id_with_viva(question_id)

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
        )
    if question.viva.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    # Call LLM to improve question
    improved = await llm_improve_question(
        question_text=question.question_text,
        answer_text=question.answer_text,
        hint=question.hint,
        instruction=data.instruction,
    )

    question_text = improved.get("question")
    answer_text = improved.get("answer")
    hint = improved.get("hint")

    if not question_text or not answer_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LLM returned invalid improved question structure",
        )

    return {
        "question_text": question_text,
        "answer_text": answer_text,
        "hint": hint,
    }
