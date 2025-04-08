from pydantic import BaseModel, Field

class NewUser(BaseModel):
    """DTO для создания пользователя"""
    name: str = Field(min_length=3)