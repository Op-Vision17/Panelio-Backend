import math
from typing import Any, Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel):
    success: bool
    message: str


class SuccessResponse(BaseResponse, Generic[T]):
    data: T


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse(BaseResponse, Generic[T]):
    data: List[T]
    meta: PaginationMeta


class ErrorResponse(BaseResponse):
    errors: Any = {}


def success_response(
    data: Any, message: str = "Operation completed successfully"
) -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def paginated_response(
    data: List[Any],
    total: int,
    page: int,
    per_page: int,
    message: str = "Data fetched successfully",
) -> dict:
    total_pages = math.ceil(total / per_page) if per_page > 0 else 0
    return {
        "success": True,
        "message": message,
        "data": data,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
    }


def error_response(message: str, errors: Any = None) -> dict:
    return {
        "success": False,
        "message": message,
        "errors": errors or {},
    }
