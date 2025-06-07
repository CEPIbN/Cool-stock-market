from pydantic import BaseModel
from typing import List


class OrderBookLevel(BaseModel):
    price: int
    qty: int




class L2OrderBook(BaseModel):
    bid_levels: List[OrderBookLevel]
    ask_levels: List[OrderBookLevel]
