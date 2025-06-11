from sqlalchemy import select
from sqlalchemy.orm import Session

from app.DTO.Request.CreateOrderBody import OrderBody
from app.models.enums.Direction import Direction
from app.models.enums.OrderStatus import OrderStatus
from app.models.models import BaseOrder, User, Balance, LimitOrder, MarketOrder
from app.utils.balance_helpers import unfreeze_balance_after_cancel, freeze_balance


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
                       base_balance : Balance,
                       eq_balance : Balance,
                       rate : int) -> BaseOrder:
    is_buy = order_body.direction == Direction.BUY
    is_market : bool = order_body.price is None
    order_data = order_body.dict(exclude_none=True)
    if is_market:
        order_data["rate"] = rate
    # Заморозка средств
    if is_buy:
        freeze_balance(eq_balance, order_body.qty * rate)
    else:
        freeze_balance(base_balance, order_body.qty)

    # Создание ордера
    order_class = MarketOrder if is_market else LimitOrder
    return order_class(
        user_id=current_user.id,
        **order_data)