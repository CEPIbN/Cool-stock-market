from sqlalchemy import desc, asc, select
from sqlalchemy.orm import Session
from uuid import UUID

from app.exceptions import CustomAPIException
from app.models.enums.Direction import Direction
from app.models.enums.ErrorType import ErrorType
from app.models.enums.OrderStatus import OrderStatus
from app.models.models import BaseOrder, MarketOrder, LimitOrder, Transaction, Balance
from app.utils.order_helpers import util_cancel_order
from app.utils.balance_helpers import spend_frozen_balance, unfreeze_remain_after_execution, block_balances


class OrderMatcher:
    def __init__(self, db: Session, base_balance : Balance, eq_balance : Balance):
        self.db = db
        self.is_buy : bool = False
        self.base_balance = base_balance
        self.eq_balance = eq_balance

    def match(self, order : BaseOrder):
        self.is_buy = order.direction == Direction.BUY
        if isinstance(order, MarketOrder):
            return self._match_market_order(order)
        return self._match_limit_order(order)

    def _match_market_order(self, order: MarketOrder):
        matched_order_ids = self._find_matching_order_ids(order)
        #total_available = sum(o.qty - o.filled for o in matched_orders)
        # if total_available < order.qty:
        #     util_cancel_order(order, self.db)
        #     raise CustomAPIException(loc=["path", "order_id"],
        #                              msg=f"Market Order has cancelled",
        #                              type_error=ErrorType.ORDER_ID)

        executed = False
        for matched_id in matched_order_ids:
            matched = self._lock_order_by_id(matched_id)
            if order.qty > matched.qty - matched.filled:
                continue
            self._apply_trade(order, matched, order.qty)
            executed = True
            break

        if executed:
            order.status = OrderStatus.EXECUTED
        else:
            order_balance_to_cancel = self.base_balance if order.direction == Direction.SELL else self.eq_balance
            util_cancel_order(self.db, order, order_balance_to_cancel)
            raise CustomAPIException(loc=["path", "order_id"],
                                     msg=f"Market Order has cancelled",
                                     type_error=ErrorType.ORDER_ID)

    def _match_limit_order(self, order: LimitOrder):
        def calculate_trade_volume(limit_order: LimitOrder, loc_matched: LimitOrder):
            return min(limit_order.qty - limit_order.filled, loc_matched.qty - loc_matched.filled)

        executed = False
        matched_order_ids = self._find_matching_order_ids(order)
        for matched_id in matched_order_ids:
            matched = self._lock_order_by_id(matched_id)
            matched_qty = calculate_trade_volume(order, matched)
            self._apply_trade(order, matched, matched_qty)
            if self._is_executed_order(order, matched_qty):
                executed = True
                break

        self._finalize_limit_order_status(order, executed)

    def _find_matching_order_ids(self, order: BaseOrder) -> list[LimitOrder]:
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
        return [row.id for row in query.all()]

    def _lock_order_by_id(self, order_id: UUID) -> LimitOrder:
        stmt = (
            select(LimitOrder)
            .where(LimitOrder.id == order_id)
            .with_for_update()
        )
        return self.db.execute(stmt).scalars().first()

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
        assets = [order.ticker, "RUB"]
        matched_balances = self._load_matched_balances(matched.user_id, assets)
        if self.is_buy:
            balance_buy = self._transfer(transaction.amount * transaction.price,
                                         self.eq_balance, matched_balances.get("RUB"))
            self._transfer(transaction.amount,
                           matched_balances.get(order.ticker), self.base_balance)
            unfreeze_remain_after_execution(order, balance_buy, transaction)

        else:
            balance_sell = self._transfer(transaction.amount * transaction.price,
                                          matched_balances.get("RUB"), self.eq_balance)
            self._transfer(transaction.amount,
                           self.base_balance, matched_balances.get(order.ticker))
            unfreeze_remain_after_execution(matched, balance_sell, transaction)

    def _transfer(self,
                  amount: int,
                  from_balance: Balance,
                  to_balance: Balance):
        if amount <= 0:
            return

        if from_balance:
            spend_frozen_balance(from_balance, amount)

        if to_balance:
            to_balance.amount += amount

        return from_balance

    def _load_matched_balances(self, user_id: UUID, assets: list[str]) -> dict[str, Balance]:
        """
        Загружает балансы с блокировкой SELECT ... FOR UPDATE,
        в предсказуемом порядке (по user_id, asset), чтобы избежать deadlock.
        """
        balances = block_balances(user_id, assets, self.db)
        return {b.ticker: b for b in balances}