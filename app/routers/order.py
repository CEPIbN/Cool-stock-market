from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing_extensions import Generator
from uuid import UUID

from app.DTO.Request.CreateOrderBody import OrderBody
from app.DTO.Response.CreateOrderResponse import CreateOrderResponse
from app.DTO.Response.OrderResponse import LimitOrderResponse, LimitOrderBody, MarketOrderResponse, MarketOrderBody, \
    BaseOrderResponse
from app.db import get_db
from app.middlewares import get_current_user_from_token
from app.models.models import User, LimitOrder, MarketOrder

router = APIRouter(
    prefix="/api/v1/order",
    tags=["order"]
)

@router.get("/", response_model=list[BaseOrderResponse])
def get_orders(current_user: User = Depends(get_current_user_from_token),
                db: Session = Depends(get_db)):
    primary_list = list(get_orders_by_user(db, current_user.id))
    return sorted(primary_list, key=lambda order: order.timestamp, reverse=True)

@router.get("/{order_id}")
def get_order(current_user: User = Depends(get_current_user_from_token),
              db: Session = Depends(get_db)):
    return

@router.post("/")
def create_order(order_body : OrderBody,
                 current_user: User = Depends(get_current_user_from_token),
                db: Session = Depends(get_db)):
    if order_body.price:
        order = LimitOrder(
            user_id=current_user.id,
            **order_body.model_fields(),
            filled=0
        )

    else:
        order = MarketOrder(
            user_id=current_user.id,
            **order_body.model_fields())

    db.add(order)
    db.commit()
    db.refresh(order)

    return CreateOrderResponse(order_id=order.id)

@router.delete("/")
def delete_order(current_user: User = Depends(get_current_user_from_token),
                db: Session = Depends(get_db)):
    return


def get_orders_by_user(db: Session, user_id: UUID) -> Generator[BaseOrderResponse, None, None]:
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
