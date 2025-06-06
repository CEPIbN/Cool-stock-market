from sqlalchemy import desc, asc
from sqlalchemy.orm import Session

from app.models.enums.Direction import Direction
from app.models.enums.OrderStatus import OrderStatus
from app.models.models import BaseOrder, MarketOrder, LimitOrder, Transaction, Balance

class OrderMatcher:
    def __init__(self, db: Session):
        self.db = db

    def match(self, order: BaseOrder):
        if isinstance(order, MarketOrder):
            return self._match_market_order(order)
        return self._match_limit_order(order)

    def _match_market_order(self, order: MarketOrder):
        matched_orders = self._find_matching_orders(order)
        total_available = sum(o.qty - o.filled for o in matched_orders)
        if total_available < order.qty:
            # order.status = OrderStatus.REJECTED
            # self.db.commit()
            return

        for match in matched_orders:
            if order.qty > match.qty - match.filled:
                continue
            self._apply_trade(order, match, order.qty)
            break

        order.status = OrderStatus.EXECUTED
        self.db.commit()

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

        self._finalize_order_status(order, executed)
        self.db.commit()

    def _find_matching_orders(self, order: BaseOrder) -> list[LimitOrder]:
        is_buy = order.direction == Direction.BUY
        ask_direction = Direction.SELL if is_buy else Direction.BUY
        query = self.db.query(LimitOrder).filter(
            LimitOrder.ticker == order.ticker,
            LimitOrder.direction == ask_direction,
            LimitOrder.status.in_([OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED])
        )
        if isinstance(order, LimitOrder):
            price_condition = (
                LimitOrder.price < order.price if is_buy else LimitOrder.price >= order.price
            )
            query = query.filter(price_condition)

        query = query.order_by(
            asc(LimitOrder.price) if is_buy else desc(LimitOrder.price),
            LimitOrder.timestamp
        )
        return query.all()

    def _apply_trade(self, order: BaseOrder, matched: LimitOrder, matched_qty: int):
        self._change_status_ask_order(matched, matched_qty)

        if hasattr(order, 'filled'):
            order.filled += matched_qty

        trade_price = self._record_transaction(order, matched, matched_qty)
        self._update_balances(order, matched, matched_qty, trade_price)

    def _change_status_ask_order(self, matched : LimitOrder, matched_qty):
        matched.filled += matched_qty
        if matched.filled == matched.qty:
            matched.status = OrderStatus.EXECUTED
        else:
            matched.status = OrderStatus.PARTIALLY_EXECUTED

    def _is_executed_order(self, order : BaseOrder, matched_qty : int):
        if isinstance(order, LimitOrder):
            return order.filled == order.qty

        return order.qty == matched_qty

    def _finalize_order_status(self, order: BaseOrder, executed : bool):
        if executed:
            order.status = OrderStatus.EXECUTED
        elif order.price and order.filled > 0:
            order.status = OrderStatus.PARTIALLY_EXECUTED

    def _record_transaction(self, order : BaseOrder, matched : LimitOrder, matched_qty : int):
        trade_price = matched.price if hasattr(matched, 'price') else order.price
        transaction = Transaction(
            ticker=order.ticker,
            amount=matched_qty,
            price=trade_price
        )
        self.db.add(transaction)
        return trade_price

    def _update_balances(self, order : BaseOrder, matched : LimitOrder, qty, price : int):
        if order.direction == Direction.BUY:
            self._transfer("RUB", order.user_id, matched.user_id, qty * price)
            self._transfer(order.ticker, matched.user_id, order.user_id, qty)
        else:
            self._transfer(order.ticker, order.user_id, matched.user_id, qty)
            self._transfer("RUB", matched.user_id, order.user_id, qty * price)

    def _transfer(self, asset: str, from_user: int, to_user: int, amount: int):
        if amount <= 0:
            return

        from_balance = self.db.get(Balance, (from_user, asset))
        to_balance = self.db.get(Balance, (to_user, asset))

        if from_balance:
            from_balance.amount -= amount
        if to_balance:
            to_balance.amount += amount