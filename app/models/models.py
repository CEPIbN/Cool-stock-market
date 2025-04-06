from sqlalchemy import Column, Integer, String
from app.db import Base


class User(Base):
    __tablename__: str = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)