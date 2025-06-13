from sqlalchemy import create_engine, QueuePool
from sqlalchemy.orm import sessionmaker, declarative_base

from os import getenv

def get_database_url():
    return getenv("DATABASE_URL")

def get_engine():
    return create_engine(get_database_url(),
                         poolclass=QueuePool,  # Использование пула соединений
                         pool_size=45,  # Максимальное количество соединений в пуле
                         max_overflow=5,  # Дополнительные соединения, которые могут быть созданы по мере необходимости
                         pool_timeout=30,  # Время ожидания получения соединения из пула
                         pool_recycle=1800
                         )

engine = get_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()