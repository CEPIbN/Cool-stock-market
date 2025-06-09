from sqlalchemy.orm import Session

from app.DTO.Request.CreateOrderBody import OrderBody
from app.models.enums.Direction import Direction
from app.models.enums.OrderStatus import OrderStatus
from app.models.models import BaseOrder, User, Balance, LimitOrder, MarketOrder
from app.utils.balance_helpers import unfreeze_balance_after_cancel, freeze_balance


def util_cancel_order(order : BaseOrder, db : Session):
    order.status = OrderStatus.CANCELLED
    unfreeze_balance_after_cancel(order, db)
    db.commit()

def create_order_entry(order_body : OrderBody,
                       current_user : User,
                       base_balance : Balance,
                       eq_balance : Balance,
                       rate : int) -> BaseOrder:
    is_buy = order_body.direction == Direction.BUY
    is_market = not hasattr(order_body, 'price')
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