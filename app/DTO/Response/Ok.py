from pydantic import BaseModel, Field

class Ok(BaseModel):
    """DTO для создания пользователя"""
    success: bool = Field(default=True)