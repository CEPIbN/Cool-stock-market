import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.models.enums.UserRole import UserRole
from app.models.models import User  # Примерная модель

def seed():
    db = SessionLocal()

    if not db.query(User).first():  # чтобы не дублировать
        admin_uuid = uuid.uuid4()
        admin = User(id=admin_uuid,
                     name="Admin",
                     role=UserRole.ADMIN,
                     api_key=f"key-{admin_uuid}")

        db.add_all([admin])
        db.commit()
        print("Seed data added!")

    db.close()