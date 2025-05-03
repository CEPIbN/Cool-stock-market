from sqlalchemy import (
    Column, Integer, String, ForeignKey, CheckConstraint,
    DateTime, func
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from app.db import Base
from app.models.enums.UserRole import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, index=False)
    name = Column(String, nullable=False)
    role = Column(ENUM(UserRole, name="user_role"), nullable=False)
    api_key = Column(String, nullable=False)


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

    __table_args__ = (
        CheckConstraint("ticker ~ '^[A-Z]{2,10}$'", name='ticker_format_check'),
    )


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
