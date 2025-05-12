from pydantic import BaseModel, Field

class InstrumentSchema(BaseModel):
    """DTO для создания пользователя"""
    name: str = Field()
    ticker: str = Field(pattern=r"^[A-Z]{2,10}$")

    class Config:
        from_attributes = True