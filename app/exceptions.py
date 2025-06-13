from typing import List, Union

from alembic.util import status
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.enums.ErrorType import ErrorType


class CustomAPIException(Exception):
    def __init__(self, loc: List[Union[str, int]],
                 msg: str,
                 type_error: ErrorType,
                 status_code : int = 400):
        self.loc = loc
        self.msg = msg
        self.type = type_error
        self.status_code = status_code

async def custom_http_validation_exception_handler(request: Request, exc: Union[RequestValidationError, HTTPException]):
    is_http_exception = isinstance(exc, HTTPException)
    if is_http_exception and 400 <= exc.status_code < 422:
        print(f"GGG[HTTP {exc.status_code}] {request.method} {request.url.path} -> {exc.detail}")

    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append({
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        })
    status_code = 400 if is_http_exception else 422
    return JSONResponse(
        status_code=status_code,
        content={"detail": formatted_errors},
    )
