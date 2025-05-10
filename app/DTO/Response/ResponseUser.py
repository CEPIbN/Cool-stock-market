from pydantic import BaseModel
from uuid import UUID


class ResponseUser(BaseModel):
    id : UUID
    name : str
    role : str
    api_key : str

    # class Config:
    #     orm_mode = True