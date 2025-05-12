from typing import List, Union

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models.enums.ErrorType import ErrorType


class CustomAPIException(Exception):
    def __init__(self, loc: List[Union[str, int]], msg: str, type_error: ErrorType):
        self.loc = loc
        self.msg = msg
        self.type = type_error

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
