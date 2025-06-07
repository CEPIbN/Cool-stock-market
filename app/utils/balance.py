from sqlalchemy.orm import Session
from uuid import UUID

from app.DTO.Request.CreateOrderBody import OrderBody
from app.exceptions import CustomAPIException
from app.models.enums.Direction import Direction
from app.models.enums.ErrorType import ErrorType
from app.models.models import Balance, BaseOrder, MarketOrder


def get_available_balance(balance: Balance) -> int:
    return balance.amount - balance.frozen_amount

def freeze_balance(balance: Balance, qty: int):
    available = get_available_balance(balance)
    if qty > available:
        raise CustomAPIException(loc=["balance", "amount"],
                                 msg=f"Not enough available balance",
                                 type_error=ErrorType.NOT_ENOUGH_FOR_WITHDRAW)
    balance.frozen_amount += qty


def unfreeze_balance(balance: Balance, qty: int):
    if qty > balance.frozen_amount:
        raise CustomAPIException(loc=["balance", "amount"],
                                 msg=f"Not enough frozen balance",
                                 type_error=ErrorType.NOT_ENOUGH_FOR_WITHDRAW)
    balance.frozen_amount -= qty

def unfreeze_balance_after_cancel(order : BaseOrder, db : Session):
    is_buy = order.direction == Direction.BUY
    ticker = "RUB" if is_buy else order.ticker
    balance = db.get(Balance, (order.user_id, ticker))

    # Определяем сумму заморозки
    if isinstance(order, MarketOrder):
        amount_to_unfreeze = order.qty * order.rate if is_buy else order.qty
    else:
        remaining_qty = order.qty - order.filled
        amount_to_unfreeze = remaining_qty * order.price if is_buy else remaining_qty

    unfreeze_balance(balance, amount_to_unfreeze)

def spend_frozen_balance(balance: Balance, qty: int):
    if qty > balance.frozen_amount:
        raise CustomAPIException(loc=["balance", "amount"],
                                 msg=f"Not enough frozen balance",
                                 type_error=ErrorType.NOT_ENOUGH_FOR_WITHDRAW)
    balance.frozen_amount -= qty
    balance.amount -= qty

def validate_balance(db : Session, order_body : OrderBody, user_id : UUID) -> [Balance, Balance, int]:
    rate = order_body.price or 1 #db.get(AssetEquivalent, (order_body.ticker, 'RUB')).rate
    base_balance = db.get(Balance, (user_id, order_body.ticker))
    if not base_balance:
        base_balance = Balance(user_id=user_id, ticker=order_body.ticker)
        db.add(base_balance)
    eq_balance = db.get(Balance, (user_id, 'RUB'))
    check_balance(order_body.direction,
                  rate,
                  order_body.qty,
                  eq_balance,
                  base_balance)

    return base_balance, eq_balance, rate

def check_balance(direction : Direction,
                  rate : int,
                  order_body_qty : int,
                  eq_balance : Balance,
                  base_balance : Balance):
    if direction == Direction.BUY:
        if rate * order_body_qty > get_available_balance(eq_balance):
            raise CustomAPIException(loc=["balance", "amount"],
                                     msg=f"Not enough equivalent tickers",
                                     type_error=ErrorType.NOT_ENOUGH_FOR_WITHDRAW)

    else:
        if get_available_balance(base_balance) < order_body_qty:
            raise CustomAPIException(loc=["balance", "amount"],
                                     msg=f"Not enough base tickers",
                                     type_error=ErrorType.NOT_ENOUGH_FOR_WITHDRAW)