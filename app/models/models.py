from sqlalchemy import Column, Integer, String, CheckConstraint
from sqlalchemy.dialects.postgresql import ENUM
from app.db import Base
from app.models.enums.UserRole import UserRole


class User(Base):
    __tablename__: str = "users"

    id = Column(String, primary_key=True, index=False)
    name = Column(String, nullable=False)
    role = Column(ENUM(UserRole, name="user_role"), nullable=False)


class Instrument(Base):
    __tablename__: str = "instruments"

    ticker = Column(String, primary_key=True, index=False)
    name = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("ticker ~ '^[A-Z]{2,10}$'", name='check_ticker_format'),
    )


# class Transaction(Base):
#     __tablename__: str = "transactions"
#
#     id = Column(Integer, primary_key=True, index=True)
#     ticker = Column(String, nullable=False)
#     amount = Column(Integer, nullable=False)
#     price = Column(Integer, nullable=False)
#     timestamp = Column(String, nullable=False)
#
#     __table_args__ = (
#         CheckConstraint("ticker ~ '^[A-Z]{2,10}$'", name='ticker_format_check'),
#     )


