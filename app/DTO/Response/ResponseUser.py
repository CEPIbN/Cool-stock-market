from pydantic import BaseModel


class ResponseUser(BaseModel):
    id : str
    name : str
    role : str