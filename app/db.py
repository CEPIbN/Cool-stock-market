from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from os import getenv

DATABASE_URL = getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()