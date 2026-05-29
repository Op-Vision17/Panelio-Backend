import random
import string
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.questions.model import Question
from app.features.vivas.dao import VivaDAO
from app.features.vivas.model import Viva
from app.features.vivas.schema import (
    QuestionCreate,
    QuestionsGenerateRequest,
    VivaCreate,
    VivaUpdate,
)
from app.shared.llm import generate_questions as llm_generate_questions


async def generate_viva_code(db: AsyncSession) -> str:
    chars = string.ascii_uppercase + string.digits
    viva_dao = VivaDAO(db)
    while True:
        code = "".join(random.choices(chars, k=6))
        existing_viva = await viva_dao.get_by_code(code)
        if not existing_viva:
            return code


async def create_viva(db: AsyncSession, data: VivaCreate, user_id) -> Viva:
    code = await generate_viva_code(db)
    viva = Viva(
        owner_id=user_id,
        name=data.name,
        code=code,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    viva_dao = VivaDAO(db)
    return await viva_dao.create(viva)


async def get_vivas(db: AsyncSession, user_id) -> list[Viva]:
    viva_dao = VivaDAO(db)
    return await viva_dao.get_by_owner(user_id)


async def get_viva_by_id(db: AsyncSession, viva_id, user_id) -> Viva:
    viva_dao = VivaDAO(db)
    viva = await viva_dao.get_by_id_with_questions(viva_id, user_id)
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva not found"
        )

    viva.questions.sort(key=lambda q: q.order_index)
    return viva


async def update_viva(db: AsyncSession, viva_id, data: VivaUpdate, user_id) -> Viva:
    viva_dao = VivaDAO(db)
    viva = await viva_dao.get_by_id_and_owner(viva_id, user_id)
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva not found"
        )

    if data.name is not None:
        viva.name = data.name
    if data.start_time is not None:
        viva.start_time = data.start_time
    if data.end_time is not None:
        viva.end_time = data.end_time

    return await viva_dao.update(viva)


async def delete_viva(db: AsyncSession, viva_id, user_id):
    viva_dao = VivaDAO(db)
    viva = await viva_dao.get_by_id_and_owner(viva_id, user_id)
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva not found"
        )

    await viva_dao.delete(viva)


async def create_viva_question(
    db: AsyncSession, viva_id: uuid.UUID, user_id: uuid.UUID, data: QuestionCreate
) -> Question:
    viva_dao = VivaDAO(db)
    viva = await viva_dao.get_viva_by_id_raw(viva_id)
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva not found"
        )
    if viva.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    max_order = await viva_dao.get_max_question_order(viva_id)
    next_order = (max_order + 1) if max_order is not None else 0

    new_question = Question(
        viva_id=viva_id,
        order_index=next_order,
        question_text=data.question_text,
        answer_text=data.answer_text,
        hint=data.hint,
    )
    return await viva_dao.create_question(new_question)


async def get_viva_questions(
    db: AsyncSession, viva_id: uuid.UUID, user_id: uuid.UUID
) -> list[Question]:
    viva_dao = VivaDAO(db)
    viva = await viva_dao.get_viva_by_id_raw(viva_id)
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva not found"
        )
    if viva.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    return await viva_dao.get_questions_by_viva_id(viva_id)


async def generate_viva_questions(
    db: AsyncSession,
    viva_id: uuid.UUID,
    user_id: uuid.UUID,
    data: QuestionsGenerateRequest,
) -> list[Question]:
    viva_dao = VivaDAO(db)
    viva = await viva_dao.get_viva_by_id_raw(viva_id)
    if not viva:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viva not found"
        )
    if viva.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    # Call LLM to generate questions
    generated = await llm_generate_questions(
        topic=data.topic, num_questions=data.num_questions, doc_text=data.doc_text
    )

    max_order = await viva_dao.get_max_question_order(viva_id)
    start_order = (max_order + 1) if max_order is not None else 0

    questions_to_create = []
    for i, item in enumerate(generated):
        question_text = item.get("question")
        answer_text = item.get("answer")
        hint = item.get("hint")

        if not question_text or not answer_text:
            continue

        q = Question(
            viva_id=viva_id,
            order_index=start_order + i,
            question_text=question_text,
            answer_text=answer_text,
            hint=hint,
        )
        questions_to_create.append(q)

    if questions_to_create:
        return await viva_dao.create_questions(questions_to_create)
    return []
