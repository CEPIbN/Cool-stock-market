from sqlalchemy.orm import Session
from uuid import UUID

from app.DTO.Request.CreateOrderBody import OrderBody
from app.exceptions import CustomAPIException
from app.models.enums.Direction import Direction
from app.models.enums.ErrorType import ErrorType
from app.models.models import Balance, BaseOrder, MarketOrder, LimitOrder, Transaction


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

def spend_frozen_balance(balance: Balance, qty : int):
    if qty > balance.frozen_amount:
        raise CustomAPIException(loc=["balance", "amount"],
                                 msg=f"Not enough frozen balance",
                                 type_error=ErrorType.NOT_ENOUGH_FOR_WITHDRAW)
    balance.frozen_amount -= qty
    balance.amount -= qty

def unfreeze_remain_after_execution(order: BaseOrder,
                                    balance: Balance,
                                    trade: Transaction):
    if order.direction != Direction.BUY: return
    freeze_rate = order.price if isinstance(order, LimitOrder) else order.rate
    # Сколько было заморожено на этот объём
    frozen_reserved = freeze_rate * trade.amount
    # Сколько реально потрачено
    actual_cost = trade.price * trade.amount
    # Остаток, который можно разморозить
    to_unfreeze = frozen_reserved - actual_cost
    if to_unfreeze <= 0:
        return
    # Не допустить отрицательного frozen_amount
    balance.frozen_amount = max(balance.frozen_amount - to_unfreeze, 0)

def validate_balance(db : Session, order_body : OrderBody, user_id : UUID) -> [Balance, Balance, int]:
    rate = order_body.price if hasattr(order_body, 'price') else estimate_market_order_rate(order_body, db)
    base_balance = db.get(Balance, (user_id, order_body.ticker))
    if not base_balance:
        base_balance = Balance(user_id=user_id, ticker=order_body.ticker)
        db.add(base_balance)
    eq_balance = db.get(Balance, (user_id, 'RUB'))
    if not eq_balance:
        eq_balance = Balance(user_id=user_id, ticker='RUB')
        db.add(eq_balance)
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

def estimate_market_order_rate(order_body : OrderBody, db: Session) -> int:
    """
    Оценка курса для замораживания средств при рыночном ордере.
    Direction - покупка или продажа, чтобы понимать какую сторону стакана анализировать.
    """
    is_buy = order_body.direction == Direction.BUY
    answer_direction = Direction.SELL if is_buy else Direction.BUY
    best_match = (
        db.query(LimitOrder)
        .filter(LimitOrder.ticker == order_body.ticker,
                LimitOrder.direction == answer_direction,
                (LimitOrder.qty - LimitOrder.filled) >= order_body.qty,
                LimitOrder.status.in_(["NEW", "PARTIALLY_EXECUTED"]))
        .order_by(LimitOrder.price.asc() if is_buy else LimitOrder.price.desc())
        .first()
    )
    if best_match and is_buy:
        return int(best_match.price * 1.02)
    elif best_match:
        return int(best_match.price)

    last_trade = (
        db.query(Transaction)
        .filter(Transaction.ticker == order_body.ticker)
        .order_by(Transaction.timestamp.desc())
        .first()
    )
    if last_trade:
        return int(last_trade.price * 1.05)

    raise CustomAPIException(
        loc=["order", "rate"],
        msg=f"Cannot determine price for {order_body.ticker}. No market data.",
        type_error=ErrorType.MARKET_ORDER
    )