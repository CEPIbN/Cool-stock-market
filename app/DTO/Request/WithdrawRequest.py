from pydantic import BaseModel, Field, conint
from uuid import UUID

class WithdrawRequest(BaseModel):
    user_id: UUID = Field(examples=["35b0884d-9a1d-47b0-91c7-eecf0ca56bc8"])
    ticker: str = Field(pattern=r"^[A-Z]{2,10}$", examples=["MEMCOIN"])
    amount: conint(gt=0) = Field(examples=[100])
