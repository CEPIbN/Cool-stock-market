import uuid

from fastapi import APIRouter, HTTPException
from fastapi import Depends
from fastapi.openapi.models import Response
from fastapi.openapi.utils import status_code_ranges
from fastapi.params import Header
from sqlalchemy import UUID
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.DTO.Request.InstrumentSchema import InstrumentSchema
from app.DTO.Response.Ok import Ok
from app.DTO.Response.ResponseUser import ResponseUser
from app.db import get_db
from app.models.enums.UserRole import UserRole
from app.models.models import User, Instrument

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"]
)

@router.delete("/user/{user_id}", response_model=ResponseUser)
def delete_user(user_id: str,
                authorization: str | None = Header(default=None),
                db: Session = Depends(get_db)):
    if is_admin(authorization, db):
        user = db.query(User).filter(uuid.UUID(user_id) == User.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        db.delete(user)
        db.commit()
        return ResponseUser(id=uuid.UUID(user_id),
                            name=user.name,
                            role=user.role,
                            api_key=user.api_key)

    return JSONResponse(content={"message": "HTTPValidationError"}, status_code=422)


@router.post("/instrument", response_model=Ok)
def add_instrument(instrument: InstrumentSchema,
                    authorization: str | None = Header(default=None),
                   db: Session = Depends(get_db)):
    if is_admin(authorization, db):
        existing = db.query(Instrument).filter(instrument.ticker == Instrument.ticker).first()
        if existing:
            raise HTTPException(status_code=400, detail="Instrument already exists")
        db.add(Instrument(ticker=instrument.ticker, name=instrument.name))
        db.commit()
        return Ok

    return JSONResponse(content={"message": "HTTPValidationError"}, status_code=422)

@router.delete("/instrument/{ticker}")
def delete_instrument():
    return

@router.post("/balance/deposit")
def deposit():
    #Метод для пополнения баланса пользователя
    return

@router.get("/balance/withdraw")
def withdraw():
    return

def is_admin(authorization_token: str,
             db: Session):
    if authorization_token is None: return False
    admin_id = authorization_token.split('-', 1)
    admin = db.query(User).get(uuid.UUID(admin_id[1]))
    return admin.role == UserRole.ADMIN
