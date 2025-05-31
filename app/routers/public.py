from uuid import uuid4

from fastapi import APIRouter
from fastapi.params import Query
from fastapi import Depends

from app.DTO.Request.InstrumentSchema import InstrumentSchema
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

@router.post("/register",
             response_model=ResponseUser)
def register_user(data: NewUser,
                  db: Session = Depends(get_db)
):
    new_uuid = uuid4()
    user = User(id=new_uuid,
                name=data.name,
                role=UserRole.USER,
                api_key=f"key-{new_uuid}")
    db.add(user)
    db.commit()
    return user


@router.get("/instrument",  response_model=list[InstrumentSchema])
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
