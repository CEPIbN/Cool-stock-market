from enum import Enum

class ErrorType(str, Enum):
    USER_ID = "Wrong user_id"
    TICKER = "Wrong ticker"
    AUTHORIZATION = "Permission denied"
    EXISTING_TICKER = "Existing ticker"
    NOT_ENOUGH_FOR_WITHDRAW = "Not valid count tickers"