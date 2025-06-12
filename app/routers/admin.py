from sqlalchemy import select, tuple_, asc
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
from app.models.enums.OrderStatus import OrderStatus
from app.models.enums.UserRole import UserRole
from app.models.models import User, Instrument, LimitOrder, Balance
from app.utils.balance_helpers import unfreeze_balance_after_cancel
from app.utils.order_helpers import util_cancel_order

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
    db.commit()
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
    db.commit()
    return Ok

@router.delete("/instrument/{ticker}", response_model=Ok)
def delete_instrument(ticker: str = Path(pattern="^[A-Z]{2,10}$"),
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    is_admin(current_user)
    instrument = validate_ticker(db, ticker)
    orders = db.execute(
        select(LimitOrder)
        .filter_by(ticker=ticker, direction=Direction.BUY)
        .order_by(asc(LimitOrder.price), LimitOrder.timestamp)
        .with_for_update()
    ).scalars().all()

    # Собираем нужные пары для блокировки балансов
    balance_keys = sorted(
        (order.user_id, order.ticker if order.direction == Direction.SELL else "RUB")
        for order in orders
    )

    balances = db.execute(
        select(Balance)
        .where(tuple_(Balance.user_id, Balance.ticker).in_(balance_keys))
        .order_by(Balance.user_id, Balance.ticker)
        .with_for_update()
    ).scalars().all()

    # Быстрый доступ
    balance_map = {(b.user_id, b.ticker): b for b in balances}

    # Отмена ордеров и разморозка
    for order in orders:
        key = (order.user_id, order.ticker if order.direction == Direction.SELL else "RUB")
        balance = balance_map.get(key)
        order.status = OrderStatus.CANCELLED
        unfreeze_balance_after_cancel(order, balance, db)

    db.delete(instrument)
    db.commit()
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

