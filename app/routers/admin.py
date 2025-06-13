from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi.params import Path

from sqlalchemy.orm import Session

from app.DTO.Request.InstrumentSchema import InstrumentSchema
from app.DTO.Response.Ok import Ok
from app.DTO.Response.ResponseUser import ResponseUser
from app.db import get_db
from app.exceptions import CustomAPIException
from app.middlewares import get_current_user
from app.models.enums.Direction import Direction
from app.models.enums.ErrorType import ErrorType
from app.models.enums.UserRole import UserRole
from app.models.models import User, Instrument
from app.utils.balance_helpers import map_locked_balances
from app.utils.order_helpers import util_cancel_order, lock_all_orders_by_ticker

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"]
)

@router.delete("/user/{user_id}", response_model=ResponseUser)
def delete_user(user_id: UUID = Path(title="User Id"),
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    is_admin(current_user)
    user = validate_user(db, user_id)

    db.delete(user)
    return ResponseUser(id=user_id,
                        name=user.name,
                        role=user.role,
                        api_key=user.api_key)


@router.post("/instrument", response_model=Ok)
def add_instrument(instrument: InstrumentSchema,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    is_admin(current_user)

    existing = db.query(Instrument).filter(instrument.ticker == Instrument.ticker).first()
    if existing:
        raise CustomAPIException(loc=["body", "ticker"],
                                 msg=f"Ticker {existing.ticker} already exists",
                                 type_error=ErrorType.EXISTING_TICKER)

    db.add(Instrument(ticker=instrument.ticker, name=instrument.name))
    return Ok

@router.delete("/instrument/{ticker}", response_model=Ok)
def delete_instrument(ticker: str = Path(pattern="^[A-Z]{2,10}$"),
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    is_admin(current_user)
    instrument = validate_ticker(db, ticker)
    # is_buy = True
    # buy_orders = lock_all_orders_by_ticker(ticker, Direction.BUY, db)
    # # Собираем нужные пары для блокировки балансов
    # buy_balance_keys = {(buy_order.user_id, "RUB") for buy_order in buy_orders}
    # buy_balance_map = map_locked_balances(sorted(buy_balance_keys), db)
    #
    # # Отмена ордеров и разморозка
    # for order in buy_orders:
    #     key = (order.user_id, "RUB")
    #     balance = buy_balance_map.get(key)
    #     util_cancel_order(db, order, balance, is_buy)

    db.delete(instrument)
    return Ok


def is_admin(current_user: User):
    if current_user.role != UserRole.ADMIN:
        raise CustomAPIException(loc=["header", "authorization"],
                                 msg="You aren't an admin!",
                                 type_error=ErrorType.AUTHORIZATION,
                                 status_code=401)

def validate_user(db: Session, user_id: UUID):
    user = db.query(User).filter(user_id == User.id).first()
    if not user:
        raise CustomAPIException(loc=["body", "user_id"],
                                 msg=f"User {user_id} not found",
                                 type_error=ErrorType.USER_ID)

    return user

def validate_ticker(db: Session, ticker: str):
    instrument = db.query(Instrument).filter(ticker == Instrument.ticker).first()
    if not instrument:
        raise CustomAPIException(loc=["body", "ticker"],
                                 msg=f"Ticker {ticker} not found",
                                 type_error=ErrorType.TICKER)

    return instrument

