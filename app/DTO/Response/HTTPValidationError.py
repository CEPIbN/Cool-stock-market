from typing import List, Union
from pydantic import BaseModel

from app.models.enums.ErrorType import ErrorType


class ValidationErrorDetail(BaseModel):
    loc: List[Union[str, int]]
    msg: str
    type: ErrorType

    class Config:
        use_enum_values = True


class HTTPValidationError(BaseModel):
    detail: List[ValidationErrorDetail]
