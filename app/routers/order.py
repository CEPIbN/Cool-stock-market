from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from typing_extensions import Generator
from uuid import UUID

from app.DTO.Request.CreateOrderBody import OrderBody
from app.DTO.Response.CreateOrderResponse import CreateOrderResponse
from app.DTO.Response.Ok import Ok
from app.DTO.Response.OrderResponse import LimitOrderResponse, LimitOrderBody, MarketOrderResponse, MarketOrderBody, \
    BaseOrderResponse, OrderResponse
from app.OrderEngine import OrderMatcher
from app.db import get_db
from app.exceptions import CustomAPIException
from app.middlewares import get_current_user
from app.models.enums.Direction import Direction
from app.models.enums.ErrorType import ErrorType
from app.models.enums.OrderStatus import OrderStatus
from app.models.models import User, LimitOrder, MarketOrder, Balance, BaseOrder, AssetEquivalent
from app.routers.admin import validate_ticker
from app.utils.balance import freeze_balance, validate_balance, unfreeze_balance_after_cancel

router = APIRouter(
    prefix="/api/v1/order",
    tags=["order"]
)

@router.get("/", response_model=list[OrderResponse])
def get_orders(current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    primary_list = list(get_orders_by_user(db, current_user.id))
    return sorted(primary_list, key=lambda order: order.timestamp, reverse=True)

@router.get("/{order_id}")
def get_order(order_id : UUID,
              current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    for model, to_response in [
        (MarketOrder, get_market_order),
        (LimitOrder, get_limit_order)
    ]:
        order = db.query(model).filter_by(user_id=current_user.id, id=order_id).first()
        if order and order.status != OrderStatus.CANCELLED:
            return to_response(order)

    raise CustomAPIException(loc=["path", "order_id"],
                             msg=f"Order with id {order_id} doesn't exist",
                             type_error=ErrorType.ORDER_ID)

@router.post("/", response_model=CreateOrderResponse)
def create_order(order_body : OrderBody,
                 current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    validate_ticker(db, order_body.ticker)
    base_balance, eq_balance, rate = validate_balance(db, order_body, current_user.id)
    order = create_order_entry(order_body, current_user, base_balance, eq_balance, rate)
    db.add(order)
    db.commit()
    db.refresh(order)

    OrderMatcher(db).match(order)
    return CreateOrderResponse(order_id=order.id)

@router.delete("/{order_id}", response_model=Ok)
def cancel_order(order_id : UUID = Path(),
                 current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    for model, to_response in [
        (MarketOrder, get_market_order),
        (LimitOrder, get_limit_order)
    ]:
        order = (db.query(model)
            .filter_by(user_id=current_user.id, id=order_id)
            .filter(model.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]))
            .first()
        )
        if isinstance(order, BaseOrder):
            order.status = OrderStatus.CANCELLED
            unfreeze_balance_after_cancel(order, db)
            db.commit()
            return Ok

    if not order:
        raise CustomAPIException(loc=["path", "order_id"],
                             msg=f"Order with id {order_id} doesn't exist",
                             type_error=ErrorType.ORDER_ID)

def get_orders_by_user(db: Session, user_id: UUID) -> Generator[OrderResponse, None, None]:
    target_statuses = [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED, OrderStatus.EXECUTED]
    for model, to_response in [
        (MarketOrder, get_market_order),
        (LimitOrder, get_limit_order)
    ]:
        orders = (db.query(model)
        .filter(model.user_id == user_id,
        model.status.in_(target_statuses))
        .all())
        for order in orders:
            yield to_response(order)

def get_market_order(order : MarketOrder) -> BaseOrderResponse:
    return MarketOrderResponse(
        id=order.id,
        status=order.status,
        user_id=order.user_id,
        timestamp=order.timestamp,
        body=MarketOrderBody(
            ticker=order.ticker,
            qty=order.qty,
            direction=order.direction,
        ),
    )

def get_limit_order(order : LimitOrder) -> BaseOrderResponse:
    return LimitOrderResponse(
        id=order.id,
        status=order.status,
        user_id=order.user_id,
        timestamp=order.timestamp,
        body=LimitOrderBody(
            ticker=order.ticker,
            qty=order.qty,
            direction=order.direction,
            price=order.price,
        ),
        filled=order.filled,
    )

def create_order_entry(order_body : OrderBody,
                       current_user : User,
                       base_balance : Balance,
                       eq_balance : Balance,
                       rate : int) -> BaseOrder:
    is_buy = order_body.direction == Direction.BUY
    order_data = order_body.dict(exclude_none=True)
    # Заморозка средств
    if is_buy:
        freeze_balance(eq_balance, order_body.qty * rate)
    else:
        freeze_balance(base_balance, order_body.qty)
    # Создание ордера
    order_class = LimitOrder if order_body.price else MarketOrder
    return order_class(
        user_id=current_user.id,
        **order_data,
        **({"rate": rate} if order_class is MarketOrder else {})
    )

def convert_to_equivalent(db: Session, amount: int, base_ticker : str, eq_ticker : str = "RUB"):
    eq_entry = (db.query(AssetEquivalent)
                .filter_by(base_ticker=base_ticker,
                equivalent_ticker=eq_ticker)
                .first())
    if not eq_entry:
        return

    return amount * eq_entry.rate




