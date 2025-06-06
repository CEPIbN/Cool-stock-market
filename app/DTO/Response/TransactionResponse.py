from datetime import datetime

from pydantic import BaseModel, Field


class TransactionResponse(BaseModel):
    id: int = Field(exclude=True)
    ticker: str = Field(pattern=r"^[A-Z]{2,10}$", examples=["RUB"])
    amount: int
    price: int
    timestamp: datetime

    class Config:
        from_attributes = True