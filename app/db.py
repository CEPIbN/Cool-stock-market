from sqlalchemy import create_engine, QueuePool
from sqlalchemy.orm import sessionmaker, declarative_base

from os import getenv

DATABASE_URL = getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL,
                       poolclass=QueuePool,  # Использование пула соединений
                       pool_size=5,  # Максимальное количество соединений в пуле
                       max_overflow=10,  # Дополнительные соединения, которые могут быть созданы по мере необходимости
                       pool_timeout=30,  # Время ожидания получения соединения из пула
                       pool_recycle=1800
                       )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#db = SessionLocal()

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()