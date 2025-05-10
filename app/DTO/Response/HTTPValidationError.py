from typing import List, Union
from pydantic import BaseModel


class ValidationErrorDetail(BaseModel):
    loc: List[Union[str, int]]
    msg: str
    type: str


class HTTPValidationError(BaseModel):
    detail: List[ValidationErrorDetail]
