import io
import uuid
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.vivas import service
from app.features.vivas.schema import (
    QuestionCreate,
    QuestionsGenerateRequest,
    QuestionsGenerateTopicRequest,
    VivaCreate,
    VivaUpdate,
)


async def handle_create_viva(data: VivaCreate, db: AsyncSession, current_user):
    return await service.create_viva(db, data, current_user.id)


async def handle_get_vivas(db: AsyncSession, current_user):
    return await service.get_vivas(db, current_user.id)


async def handle_get_viva(viva_id, db: AsyncSession, current_user):
    return await service.get_viva_by_id(db, viva_id, current_user.id)


async def handle_update_viva(viva_id, data: VivaUpdate, db: AsyncSession, current_user):
    return await service.update_viva(db, viva_id, data, current_user.id)


async def handle_delete_viva(viva_id, db: AsyncSession, current_user):
    await service.delete_viva(db, viva_id, current_user.id)


async def handle_create_viva_question(
    viva_id: uuid.UUID, data: QuestionCreate, db: AsyncSession, current_user
):
    return await service.create_viva_question(db, viva_id, current_user.id, data)


async def handle_get_viva_questions(viva_id: uuid.UUID, db: AsyncSession, current_user):
    return await service.get_viva_questions(db, viva_id, current_user.id)


async def extract_text_from_file(file: UploadFile) -> str:
    filename = file.filename.lower()
    content = await file.read()

    if filename.endswith(".pdf"):
        try:
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            extracted_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
            return extracted_text.strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse PDF file: {str(e)}",
            )
    elif filename.endswith((".txt", ".md", ".json", ".csv")):
        try:
            return content.decode("utf-8").strip()
        except UnicodeDecodeError:
            try:
                return content.decode("latin-1").strip()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to decode text file: {str(e)}",
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a PDF or plain text file.",
        )


async def handle_generate_viva_questions_from_topic(
    viva_id: uuid.UUID,
    data: QuestionsGenerateTopicRequest,
    db: AsyncSession,
    current_user,
):
    gen_data = QuestionsGenerateRequest(
        topic=data.topic,
        num_questions=data.num_questions,
        doc_text=None,
    )
    return await service.generate_viva_questions(db, viva_id, current_user.id, gen_data)


async def handle_generate_viva_questions_from_document(
    viva_id: uuid.UUID,
    num_questions: int,
    doc_text: Optional[str],
    doc_file: Optional[UploadFile],
    db: AsyncSession,
    current_user,
):
    extracted_text = None
    if doc_file and doc_file.filename:
        extracted_text = await extract_text_from_file(doc_file)
        if not extracted_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract any text content from the uploaded document.",
            )

    final_doc_text = extracted_text if extracted_text else doc_text

    if not final_doc_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text or file is required.",
        )

    # Use the viva name as the topic for generation
    viva = await service.get_viva_by_id(db, viva_id, current_user.id)
    final_topic = viva.name

    gen_data = QuestionsGenerateRequest(
        topic=final_topic,
        num_questions=num_questions,
        doc_text=final_doc_text,
    )
    return await service.generate_viva_questions(db, viva_id, current_user.id, gen_data)


async def handle_get_viva_sessions(viva_id, db: AsyncSession, current_user):
    return await service.get_viva_sessions(db, viva_id, current_user.id)
