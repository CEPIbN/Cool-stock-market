from sqlalchemy import select, asc, desc
from sqlalchemy.orm import Session
from uuid import UUID

from app.DTO.Request.CreateOrderBody import OrderBody
from app.models.enums.Direction import Direction
from app.models.enums.OrderStatus import OrderStatus
from app.models.models import BaseOrder, User, Balance, LimitOrder, MarketOrder
from app.utils.balance_helpers import unfreeze_balance_after_cancel, ensure_balances_exist, estimate_market_order_rate


def util_cancel_order(db : Session, order : BaseOrder, balance : Balance = None):
    order.status = OrderStatus.CANCELLED
    if balance is None:
        balance_stmt = select(Balance).where(
            (Balance.user_id == order.user_id) &
            (Balance.ticker == order.ticker if order.direction == Direction.SELL else Balance.ticker == "RUB")
        ).with_for_update()
        balance = db.execute(balance_stmt).scalars().first()
    unfreeze_balance_after_cancel(order, balance, db)
    db.commit()

def create_order_entry(order_body : OrderBody,
                       current_user : User,
                       rate : int) -> (BaseOrder, int, bool):
    is_buy = order_body.direction == Direction.BUY
    is_market : bool = order_body.price is None
    order_data = order_body.dict(exclude_none=True)
    if is_market:
        order_data["rate"] = rate
    # Заморозка средств
    if is_buy:
        freeze_balance = order_body.qty * rate
        #freeze_balance(eq_balance, order_body.qty * rate)
    else:
        freeze_balance = order_body.qty
        #freeze_balance(base_balance, order_body.qty)

    # Создание ордера
    order_class = MarketOrder if is_market else LimitOrder
    return (order_class(
        user_id=current_user.id,
        **order_data), freeze_balance, is_buy)

def get_rate(db : Session, order_body : OrderBody, user_id : UUID):
    ensure_balances_exist(db, user_id, [order_body.ticker, 'RUB'])
    return estimate_market_order_rate(order_body, db) if order_body.price is None else order_body.price

def find_matching_order_ids(db : Session, order: BaseOrder) -> list[LimitOrder]:
    is_buy = order.direction == Direction.BUY
    ask_direction = Direction.SELL if is_buy else Direction.BUY
    query = db.query(LimitOrder).filter(
        LimitOrder.ticker == order.ticker,
        LimitOrder.direction == ask_direction,
        LimitOrder.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
    )
    if isinstance(order, LimitOrder):
        price_condition = (
            LimitOrder.price <= order.price if is_buy else LimitOrder.price >= order.price
        )
        query = query.filter(price_condition)

    query = query.order_by(
        asc(LimitOrder.price) if is_buy else desc(LimitOrder.price),
        LimitOrder.timestamp
    )

    return [row.id for row in query.all()]