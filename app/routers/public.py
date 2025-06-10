from sqlalchemy import func, select
from uuid import uuid4

from fastapi import APIRouter
from fastapi.params import Query, Path
from fastapi import Depends

from app.DTO.Request.InstrumentSchema import InstrumentSchema
from app.DTO.Response.OrderBook import L2OrderBook, OrderBookLevel
from app.DTO.Response.TransactionResponse import TransactionResponse
from app.models.enums.Direction import Direction
from app.models.enums.OrderStatus import OrderStatus
from app.models.models import User, Instrument, Balance, Transaction, LimitOrder
from app.DTO.Request.NewUser import NewUser
from app.DTO.Response.ResponseUser import ResponseUser

from app.models.enums.UserRole import UserRole
from fastapi.responses import Response
from app.db import get_db
from sqlalchemy.orm import Session

from app.routers.admin import validate_ticker

router = APIRouter(
    prefix="/api/v1/public",
    tags=["public"]
)

@router.post("/register", response_model=ResponseUser)
def register_user(data: NewUser,
                  db: Session = Depends(get_db)
):
    new_uuid = uuid4()
    user = User(id=new_uuid,
                name=data.name,
                role=UserRole.USER,
                api_key=f"key-{new_uuid}")
    db.add(user)
    db.add(Balance(user_id=new_uuid, ticker="RUB"))
    db.commit()
    return user

@router.get("/instrument",  response_model=list[InstrumentSchema])
def get_instruments(db: Session = Depends(get_db)):
    stmt = select(Instrument)
    return db.execute(stmt).scalars().all()

@router.get("/orderbook/{ticker}", response_model=L2OrderBook)
def get_orderbook(ticker: str = Path(pattern="^[A-Z]{2,10}$"),
                  limit: int = Query(default=10, gt=0, le=25),
                  db: Session = Depends(get_db)):
    bid_levels = (
        db.query(LimitOrder.price,
        func.sum(LimitOrder.qty - LimitOrder.filled).label("qty")
    )
    .filter(
        LimitOrder.ticker == ticker,
        LimitOrder.direction == Direction.BUY,
        LimitOrder.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
    )
    .group_by(LimitOrder.price)
    .order_by(LimitOrder.price.desc())
    .limit(limit)
    .all())

    ask_levels = (
        db.query(LimitOrder.price,
        func.sum(LimitOrder.qty - LimitOrder.filled).label("qty")
    )
    .filter(
        LimitOrder.ticker == ticker,
        LimitOrder.direction == Direction.SELL,
        LimitOrder.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
    )
    .group_by(LimitOrder.price)
    .order_by(LimitOrder.price.asc())
    .limit(limit)
    .all())

    return L2OrderBook(
        bid_levels=[OrderBookLevel(price=row.price, qty=row.qty) for row in bid_levels],
        ask_levels=[OrderBookLevel(price=row.price, qty=row.qty) for row in ask_levels]
    )


@router.get("/transactions/{ticker}", response_model=list[TransactionResponse])
def get_transactions(ticker: str = Path(pattern="^[A-Z]{2,10}$"),
                     limit: int = Query(default=10, gt=0, le=25),
                     db: Session = Depends(get_db)):
    validate_ticker(db, ticker)
    stmt = (
        select(Transaction).order_by(
            Transaction.timestamp.desc()
        )
        .limit(limit)
    )
    return db.execute(stmt).scalars().all()
