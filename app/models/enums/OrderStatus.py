from enum import Enum

class OrderStatus(Enum):
    NEW = "new"
    EXECUTED = "executed"
    PARTIALLY_EXECUTED = "partially_executed"
    CANCELLED = "cancelled"