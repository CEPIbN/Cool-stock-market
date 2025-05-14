from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.db import get_db
from app.middlewares import get_current_user_from_token
from app.models.models import User, Balance

router_balance = APIRouter(
    prefix="/api/v1/balance",
    tags=["balance"]
)

router_admin_balance = APIRouter(
    prefix="/api/v1/admin/balance",
    tags=["admin_balance"]
)

@router_balance.get("/")
def get_balance(current_user: User = Depends(get_current_user_from_token),
                db: Session = Depends(get_db)):
    balances = db.query(Balance).filter(current_user.id == Balance.user_id)
    balances_dict = {i.ticker: i.amount for i in balances}
    return JSONResponse(content=balances_dict, status_code=200)

@router_admin_balance.post("/deposit")
def deposit_balance():
    return

@router_admin_balance.post("/deposit")
def withdraw_balance():
    return