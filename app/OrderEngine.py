from sqlalchemy import desc, asc
from sqlalchemy.orm import Session

from app.exceptions import CustomAPIException
from app.models.enums.Direction import Direction
from app.models.enums.ErrorType import ErrorType
from app.models.enums.OrderStatus import OrderStatus
from app.models.models import BaseOrder, MarketOrder, LimitOrder, Transaction, Balance
from app.utils.order_helpers import util_cancel_order
from app.utils.balance_helpers import spend_frozen_balance, unfreeze_remain_after_execution


class OrderMatcher:
    def __init__(self, db: Session):
        self.db = db
        self.is_buy : bool = False
    def match(self, order : BaseOrder):
        self.is_buy = order.direction == Direction.BUY
        if isinstance(order, MarketOrder):
            return self._match_market_order(order)
        return self._match_limit_order(order)

    def _match_market_order(self, order: MarketOrder):
        matched_orders = self._find_matching_orders(order)
        total_available = sum(o.qty - o.filled for o in matched_orders)
        if total_available < order.qty:
            util_cancel_order(order, self.db)
            raise CustomAPIException(loc=["path", "order_id"],
                                     msg=f"Market Order has cancelled",
                                     type_error=ErrorType.ORDER_ID)

        executed = False
        for match in matched_orders:
            if order.qty > match.qty - match.filled:
                continue
            self._apply_trade(order, match, order.qty)
            executed = True
            break

        if executed:
            order.status = OrderStatus.EXECUTED
            self.db.commit()
        else:
            util_cancel_order(order, self.db)
            raise CustomAPIException(loc=["path", "order_id"],
                                     msg=f"Market Order has cancelled",
                                     type_error=ErrorType.ORDER_ID)

    def _match_limit_order(self, order: LimitOrder):
        def calculate_trade_volume(limit_order: LimitOrder, loc_matched: LimitOrder):
            return min(limit_order.qty - limit_order.filled, loc_matched.qty - loc_matched.filled)

        executed = False
        matched_orders = self._find_matching_orders(order)
        for matched in matched_orders:
            matched_qty = calculate_trade_volume(order, matched)
            self._apply_trade(order, matched, matched_qty)
            if self._is_executed_order(order, matched_qty):
                executed = True
                break

        self._finalize_limit_order_status(order, executed)
        self.db.commit()

    def _find_matching_orders(self, order: BaseOrder) -> list[LimitOrder]:
        ask_direction = Direction.SELL if self.is_buy else Direction.BUY
        query = self.db.query(LimitOrder).filter(
            LimitOrder.ticker == order.ticker,
            LimitOrder.direction == ask_direction,
            LimitOrder.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
        )
        if isinstance(order, LimitOrder):
            price_condition = (
                LimitOrder.price <= order.price if self.is_buy else LimitOrder.price >= order.price
            )
            query = query.filter(price_condition)

        query = query.order_by(
            asc(LimitOrder.price) if self.is_buy else desc(LimitOrder.price),
            LimitOrder.timestamp
        )
        return query.all()

    def _apply_trade(self, order: BaseOrder, matched: LimitOrder, matched_qty: int):
        self._change_status_match_order(matched, matched_qty)

        if hasattr(order, 'filled'):
            order.filled += matched_qty

        transaction = self._record_transaction(order, matched, matched_qty)
        self._update_balances(order, matched, transaction)

    def _change_status_match_order(self, matched : LimitOrder, matched_qty):
        matched.filled += matched_qty
        if matched.filled == matched.qty:
            matched.status = OrderStatus.EXECUTED
        else:
            matched.status = OrderStatus.PARTIALLY_EXECUTED

    def _is_executed_order(self, order : BaseOrder, matched_qty : int):
        if isinstance(order, LimitOrder):
            return order.filled == order.qty

        return order.qty == matched_qty

    def _finalize_limit_order_status(self, order: LimitOrder, executed : bool):
        if executed:
            order.status = OrderStatus.EXECUTED

        elif order.filled > 0:
            order.status = OrderStatus.PARTIALLY_EXECUTED

    def _record_transaction(self, order : BaseOrder, matched : LimitOrder, matched_qty : int) -> Transaction:
        trade_price = matched.price  # matched всегда лимитный ордер
        transaction = Transaction(
            ticker=order.ticker,
            amount=matched_qty,
            price=trade_price
        )
        self.db.add(transaction)
        return transaction

    def _update_balances(self, order : BaseOrder, matched : LimitOrder, transaction : Transaction):
        if self.is_buy:
            balance_buy = self._transfer("RUB", order, matched, transaction,
                           transaction.amount * transaction.price)
            self._transfer(order.ticker, matched, order, transaction,
                           transaction.amount)
            unfreeze_remain_after_execution(order, balance_buy, transaction)

        else:
            self._transfer(order.ticker, order, matched, transaction,
                           transaction.amount)
            balance_sell = self._transfer("RUB", matched, order, transaction,
                           transaction.amount * transaction.price)
            unfreeze_remain_after_execution(matched, balance_sell, transaction)

    def _transfer(self, asset: str,
                  order: BaseOrder,
                  matched: LimitOrder,
                  amount : int):
        if amount <= 0:
            return

        from_balance = self.db.get(Balance, (order.user_id, asset))
        to_balance = self.db.get(Balance, (matched.user_id, asset))

        if from_balance:
            spend_frozen_balance(from_balance, amount)

        if to_balance:
            to_balance.amount += amount

        return from_balance