import uuid
from sqlalchemy import (
    Column, Integer, String, ForeignKey, CheckConstraint,
    DateTime, func, UniqueConstraint, Enum, UUID
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


class Instrument(Base):
    __tablename__ = "instruments"

    ticker = Column(String, primary_key=True, index=False)
    name = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("ticker ~ '^[A-Z]{2,10}$'", name='check_ticker_format'),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, ForeignKey("instruments.ticker"), nullable=False)
    amount = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Balance(Base):
    __tablename__ = "balances"
    __table_args__ = (UniqueConstraint('user_id', 'ticker', name='uq_user_ticker'),)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ticker = Column(String, ForeignKey("instruments.ticker", ondelete="CASCADE"), primary_key=True)
    amount = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="balances")


class Deposit(Base):
    __tablename__ = "deposits"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, ForeignKey("instruments.ticker"), nullable=False)
    amount = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_deposit_amount_positive"),
    )


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, ForeignKey("instruments.ticker"), nullable=False)
    amount = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount > 0", name="check_withdrawal_amount_positive"),
    )


class LimitOrder(Base):
    __tablename__ = "limit_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ticker = Column(String, ForeignKey("instruments.ticker"), nullable=False)
    direction = Column(Enum(Direction, name="direction"), nullable=False)
    qty = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
    filled = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime(timezone=True), nullable=False)


class MarketOrder(Base):
    __tablename__ = "market_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ticker = Column(String, ForeignKey("instruments.ticker"), nullable=False)
    direction = Column(Enum(Direction), nullable=False)
    qty = Column(Integer, nullable=False)
    status = Column(Enum(OrderStatus), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)





