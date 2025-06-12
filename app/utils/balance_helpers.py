from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session
from uuid import UUID

from app.DTO.Request.CreateOrderBody import OrderBody
from app.exceptions import CustomAPIException
from app.models.enums.Direction import Direction
from app.models.enums.ErrorType import ErrorType
from app.models.enums.OrderStatus import OrderStatus
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

def unfreeze_balance_after_cancel(order : BaseOrder, balance : BaseOrder, db : Session):
    is_buy = order.direction == Direction.BUY
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
                                 msg=f"Not enough balance for execute order",
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

def ensure_balances_exist(db: Session, user_id: UUID, tickers: list[str]):
    created = False
    for ticker in tickers:
        balance = db.get(Balance, (user_id, ticker))
        if not balance:
            db.add(Balance(user_id=user_id, ticker=ticker))
            created = True

    if created:
        db.flush()

# def block_balances(user_id : UUID, assets : list[str], db : Session):
#     keys = ([(user_id, ticker) for ticker in assets])
#     balances = db.execute(
#         select(Balance)
#         .where(tuple_(Balance.user_id, Balance.ticker).in_(keys))
#         .order_by(Balance.user_id, Balance.ticker)  # обязательно!
#         .with_for_update()
#     ).scalars().all()
#
#     return balances

def validate_balance(rate : int,
                     order_body : OrderBody,
                     user_id : UUID,
                     balances : dict[(UUID, str), Balance]) -> [Balance, Balance]:
    base_balance = balances.get((user_id, order_body.ticker))
    eq_balance = balances.get((user_id, "RUB"))
    check_balance(order_body.direction,
                  rate,
                  order_body.qty,
                  eq_balance,
                  base_balance)
    return base_balance, eq_balance

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
        db.execute(
            select(LimitOrder).where(
                (LimitOrder.ticker == order_body.ticker) &
                (LimitOrder.direction == answer_direction) &
                #((LimitOrder.qty - LimitOrder.filled) >= order_body.qty) &
                LimitOrder.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
            )
            .order_by(LimitOrder.price.asc() if is_buy else LimitOrder.price.desc())
        )
        .scalars()
        .first()
    )
    if best_match and is_buy:
        return int(best_match.price * 1.02)
    elif best_match:
        return int(best_match.price)

    last_trade = (
        db.execute(
            select(Transaction).where(
                Transaction.ticker == order_body.ticker
            )
            .order_by(Transaction.timestamp.desc())
        )
        .scalars()
        .first()
    )
    if last_trade:
        return int(last_trade.price * 1.05)

    raise CustomAPIException(
        loc=["order", "rate"],
        msg=f"Cannot determine price for {order_body.ticker}. No market data.",
        type_error=ErrorType.MARKET_ORDER
    )

def lock_all_balances(order: OrderBody, matched_orders: list[UUID], db : Session) -> dict[(UUID, str), Balance]:
    user_ids = set([order.user_id] + matched_orders)
    tickers = ['RUB', order.ticker]  # максимум 2 тикера
    keys = sorted((user_id, ticker) for user_id in user_ids for ticker in tickers)

    balances = db.execute(
        select(Balance)
        .where(tuple_(Balance.user_id, Balance.ticker).in_(keys))
        .order_by(Balance.user_id, Balance.ticker)
        .with_for_update()
    ).scalars().all()

    balances_dict = {(b.user_id, b.ticker): b for b in balances}
    return balances_dict