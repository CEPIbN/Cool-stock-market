from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing_extensions import Generator
from uuid import UUID

from app.DTO.Request.CreateOrderBody import OrderBody
from app.DTO.Response.CreateOrderResponse import CreateOrderResponse
from app.DTO.Response.OrderResponse import LimitOrderResponse, LimitOrderBody, MarketOrderResponse, MarketOrderBody, \
    BaseOrderResponse, OrderResponse
from app.db import get_db
from app.exceptions import CustomAPIException
from app.middlewares import get_current_user_from_token
from app.models.enums.ErrorType import ErrorType
from app.models.models import User, LimitOrder, MarketOrder
from app.routers.admin import validate_ticker

router = APIRouter(
    prefix="/api/v1/order",
    tags=["order"]
)

@router.get("/", response_model=list[OrderResponse])
def get_orders(current_user: User = Depends(get_current_user_from_token),
                db: Session = Depends(get_db)):
    primary_list = list(get_orders_by_user(db, current_user.id))
    return sorted(primary_list, key=lambda order: order.timestamp, reverse=True)

@router.get("/{order_id}")
def get_order(order_id : UUID,
              current_user: User = Depends(get_current_user_from_token),
              db: Session = Depends(get_db)):
    for model, to_response in [
        (MarketOrder, get_market_order),
        (LimitOrder, get_limit_order)
    ]:
        order = db.query(model).filter_by(user_id=current_user.id, id=order_id).first()
        if order:
            return to_response(order)

    raise CustomAPIException(loc=["path", "order_id"],
                             msg=f"Order with id {order_id} doesn't exist",
                             type_error=ErrorType.ORDER_ID)

@router.post("/", response_model=CreateOrderResponse)
def create_order(order_body : OrderBody,
                 current_user: User = Depends(get_current_user_from_token),
                 db: Session = Depends(get_db)):
    validate_ticker(db, order_body.ticker)
    if order_body.price:
        order = LimitOrder(
            user_id=current_user.id,
            **order_body.dict(exclude_none=True),
            filled=0
        )

    else:
        order = MarketOrder(
            user_id=current_user.id,
            **order_body.dict(exclude_none=True))

    db.add(order)
    db.commit()
    db.refresh(order)

    return CreateOrderResponse(order_id=order.id)

@router.delete("/")
def delete_order(current_user: User = Depends(get_current_user_from_token),
                db: Session = Depends(get_db)):
    return


def get_orders_by_user(db: Session, user_id: UUID) -> Generator[OrderResponse, None, None]:
    for model, to_response in [
        (MarketOrder, get_market_order),
        (LimitOrder, get_limit_order)
    ]:
        orders = db.query(model).filter_by(user_id=user_id).all()
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
