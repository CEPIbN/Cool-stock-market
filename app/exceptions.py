from typing import List, Union

from alembic.util import status
from fastapi import Request
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

async def custom_http_validation_exception_handler(request: Request, exc: RequestValidationError):
    formatted_errors = []
    for error in exc.errors():
        formatted_errors.append({
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        })

    return JSONResponse(
        status_code=422,
        content={"detail": formatted_errors},
    )
