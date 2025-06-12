from datetime import datetime

import uuid
from sqlalchemy import (
    Column, Integer, String, ForeignKey, CheckConstraint,
    DateTime, func, UniqueConstraint, Enum, UUID, Index
)

from sqlalchemy.orm import relationship

from app.db import Base
from app.models.enums.Direction import Direction
from app.models.enums.OrderStatus import OrderStatus
from app.models.enums.UserRole import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, index=False)
    name = Column(String, nullable=False)
    role = Column(Enum(UserRole, name="user_role"), nullable=False)
    api_key = Column(String, nullable=False)

    balances = relationship("Balance", back_populates="user", passive_deletes=True)
    limit_orders = relationship("LimitOrder", back_populates="user", passive_deletes=True)
    market_orders = relationship("MarketOrder", back_populates="user", passive_deletes=True)

class Instrument(Base):
    __tablename__ = "instruments"

    ticker = Column(String, primary_key=True, index=False)
    name = Column(String, nullable=False)

    balances = relationship("Balance", back_populates="instrument", passive_deletes=True)
    limit_orders = relationship("LimitOrder", back_populates="instrument", passive_deletes=True)
    market_orders = relationship("MarketOrder", back_populates="instrument", passive_deletes=True)
    transactions = relationship("Transaction", back_populates="instrument", passive_deletes=True)

    __table_args__ = (
        CheckConstraint("ticker ~ '^[A-Z]{2,10}$'", name='check_ticker_format'),
    )

class AssetEquivalent(Base):
    __tablename__ = "asset_equivalents"

    base_ticker = Column(String, ForeignKey("instruments.ticker"), primary_key=True)
    equivalent_ticker = Column(String, ForeignKey("instruments.ticker"), primary_key=True)

    rate = Column(Integer, nullable=False, default=1)

    base = relationship("Instrument", foreign_keys=[base_ticker], backref="equivalent_mapping")
    equivalent = relationship("Instrument", foreign_keys=[equivalent_ticker])

    __table_args__ = (
        UniqueConstraint('base_ticker', 'equivalent_ticker', name="uq_base_ticker"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, ForeignKey("instruments.ticker", ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now)

    instrument = relationship("Instrument", back_populates="transactions")

class Balance(Base):
    __tablename__ = "balances"
    __table_args__ = (UniqueConstraint('user_id', 'ticker', name='uq_user_ticker'),
                      CheckConstraint('frozen_amount <= amount', name='check_frozen_le_amount'),
                      Index('ix_balances_user_id_ticker', 'user_id', 'ticker'),)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ticker = Column(String, ForeignKey("instruments.ticker", ondelete="CASCADE"), primary_key=True)
    amount = Column(Integer, nullable=False, default=0)
    frozen_amount = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="balances")
    instrument = relationship("Instrument", back_populates="balances")


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, ForeignKey("instruments.ticker"), nullable=False)
    amount = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now)

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_deposit_amount_positive"),
    )


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, ForeignKey("instruments.ticker"), nullable=False)
    amount = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now)

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_withdrawal_amount_positive"),
    )

class BaseOrder(Base):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String, ForeignKey("instruments.ticker", ondelete="CASCADE"), nullable=False)
    direction = Column(Enum(Direction, name="direction"), nullable=False)
    qty = Column(Integer, nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.NEW)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.now)

class LimitOrder(BaseOrder):
    __tablename__ = "limit_orders"

    price = Column(Integer, nullable=False)
    filled = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="limit_orders")
    instrument = relationship("Instrument", back_populates="limit_orders")

class MarketOrder(BaseOrder):
    __tablename__ = "market_orders"

    rate = Column(Integer, nullable=False)

    user = relationship("User", back_populates="market_orders")
    instrument = relationship("Instrument", back_populates="market_orders")





