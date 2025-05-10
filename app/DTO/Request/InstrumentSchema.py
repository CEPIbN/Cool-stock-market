from pydantic import BaseModel, Field

class InstrumentSchema(BaseModel):
    """DTO для создания пользователя"""
    name: str = Field()
    ticker: str = Field()