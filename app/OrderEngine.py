from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.exceptions import CustomAPIException
from app.models.enums.Direction import Direction
from app.models.enums.ErrorType import ErrorType
from app.models.enums.OrderStatus import OrderStatus
from app.models.models import BaseOrder, MarketOrder, LimitOrder, Transaction, Balance
from app.utils.balance_helpers import spend_frozen_balance, unfreeze_remain_after_execution


class OrderMatcher:
    def __init__(self, db: Session,
                 base_balance : Balance,
                 eq_balance : Balance,
                 matched_balances : dict[(UUID, str), Balance]):
        self.db = db
        self.is_buy : bool = False
        self.base_balance = base_balance
        self.eq_balance = eq_balance
        self.matched_balances = matched_balances

    def match(self, order : BaseOrder,
              matched_orders : list[LimitOrder]):
        self.is_buy = order.direction == Direction.BUY
        if isinstance(order, MarketOrder):
            return self._match_market_order(order, matched_orders)
        return self._match_limit_order(order, matched_orders)

    def _match_market_order(self, order: MarketOrder,
                            matched_orders : list[LimitOrder]):
        executed = False
        for matched in matched_orders:
            if order.qty > matched.qty - matched.filled:
                continue
            self._apply_trade(order, matched, order.qty)
            executed = True
            break

        if executed:
            order.status = OrderStatus.EXECUTED
        else:
            raise CustomAPIException(loc=["path", "order_id"],
                                     msg=f"Market Order has cancelled",
                                     type_error=ErrorType.ORDER_ID)

    def _match_limit_order(self, order: LimitOrder,
                           matched_orders : list[LimitOrder]):
        def calculate_trade_volume(limit_order: LimitOrder, loc_matched: LimitOrder):
            return min(limit_order.qty - limit_order.filled, loc_matched.qty - loc_matched.filled)

        executed = False
        for matched in matched_orders:
            matched_qty = calculate_trade_volume(order, matched)
            self._apply_trade(order, matched, matched_qty)
            if self._is_executed_order(order, matched_qty):
                executed = True
                break

        self._finalize_limit_order_status(order, executed)

    def _lock_order_by_id(self, order_id: UUID) -> LimitOrder:
        stmt = (
            select(LimitOrder)
            .where(LimitOrder.id == order_id)
            .with_for_update()
        )
        return self.db.execute(stmt).scalars().first()

    def _apply_trade(self, order: BaseOrder,
                     matched: LimitOrder,
                     matched_qty: int):
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

    def _update_balances(self, order : BaseOrder,
                         matched : LimitOrder,
                         transaction : Transaction):
        matched_eq_balance = self.matched_balances.get((matched.user_id, "RUB"))
        matched_base_balance = self.matched_balances.get((matched.user_id, order.ticker))
        if self.is_buy:
            balance_buy = self._transfer(transaction.amount * transaction.price,
                                         self.eq_balance, matched_eq_balance)
            self._transfer(transaction.amount,
                           matched_base_balance, self.base_balance)
            unfreeze_remain_after_execution(order, balance_buy, transaction)

        else:
            balance_sell = self._transfer(transaction.amount * transaction.price,
                                          matched_eq_balance, self.eq_balance)
            self._transfer(transaction.amount,
                           self.base_balance, matched_base_balance)
            unfreeze_remain_after_execution(matched, balance_sell, transaction)

    def _transfer(self,
                  amount: int,
                  from_balance: Balance,
                  to_balance: Balance):
        if amount <= 0:
            return

        if from_balance:
            spend_frozen_balance(self.db, from_balance, amount)

        if to_balance:
            to_balance.amount += amount

        return from_balance