from fastapi import APIRouter, HTTPException
from fastapi.params import Query
from fastapi import Depends
import uuid


from app.DTO.Response.ResponseInstrument import InstrumentResponse
from app.models.models import User, Instrument
from app.DTO.Request.NewUser import NewUser
from app.DTO.Response.ResponseUser import ResponseUser

from app.models.enums.UserRole import UserRole
from fastapi.responses import Response
from app.db import get_db
from sqlalchemy.orm import Session


router = APIRouter(
    prefix="/api/v1/public",
    tags=["public"]
)

@router.post("/register",  response_model=ResponseUser)
def register_user(data: NewUser,
                  db: Session = Depends(get_db)
):
    print(data)
    user = User()
    user.name = data.name
    user.role = UserRole.USER
    user.id = str(uuid.uuid4())
    db.add(user)
    db.commit()
    return ResponseUser(id=user.id,
                        name=user.name,
                        role=user.role)


@router.get("/instrument",  response_model=list[InstrumentResponse])
def get_instruments(db: Session = Depends(get_db)):
    return db.query(Instrument).all()

@router.get("orderbook/{ticker}")
def get_orderbook(ticker: str,
                  limit: int = Query(default=10, gt=0, le=25)):
    return Response(status_code=200)

@router.get("/transactions/{ticker}")
def get_transactions(ticker: str,
                  limit: int = Query(default=10, gt=0, le=25)):
    return Response(status_code=200)
