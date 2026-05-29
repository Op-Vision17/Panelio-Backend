import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.database import Base, engine
from app.core.redis import get_redis
from app.features.attend.router import router as attend_router
from app.features.auth.router import router as auth_router
from app.features.questions.router import router as questions_router
from app.features.vivas.router import router as vivas_router
from app.shared.responses import error_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Panelio API")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(message=str(exc.detail)),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = {}
    for error in exc.errors():
        loc = " -> ".join(str(x) for x in error.get("loc", []))
        errors[loc] = error.get("msg", "Validation error")
    return JSONResponse(
        status_code=422,
        content=error_response(message="Validation failed", errors=errors),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.exception("Unhandled error occurred")
    return JSONResponse(
        status_code=500,
        content=error_response(
            message="Internal Server Error", errors={"detail": str(exc)}
        ),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # Ping DB
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    # Ping Redis
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(vivas_router, prefix="/vivas", tags=["Vivas"])
app.include_router(questions_router, prefix="/questions", tags=["Questions"])
app.include_router(attend_router, prefix="/attend", tags=["Attend"])


@app.get("/")
async def root():
    return {"message": "Welcome to Panelio API"}
