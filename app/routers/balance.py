from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.DTO.Request.DepositRequest import DepositRequest
from app.DTO.Request.WithdrawRequest import WithdrawRequest
from app.DTO.Response.Ok import Ok
from app.db import get_db
from app.exceptions import CustomAPIException
from app.middlewares import get_current_user
from app.models.enums.ErrorType import ErrorType
from app.models.models import User, Balance
from app.routers.admin import is_admin, validate_user, validate_ticker

router_balance = APIRouter(
    prefix="/api/v1/balance",
    tags=["balance"]
)

router_admin_balance = APIRouter(
    prefix="/api/v1/admin/balance",
    tags=["admin", "balance"]
)

@router_balance.get("")
def get_balance(current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    balances = db.query(Balance).filter(current_user.id == Balance.user_id)
    balances_dict = {i.ticker: i.amount for i in balances}
    return JSONResponse(content=balances_dict, status_code=200)

@router_admin_balance.post("/deposit", response_model=Ok)
def deposit_balance(deposit_data: DepositRequest,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    is_admin(current_user)

    user = validate_user(db, deposit_data.user_id)
    instrument = validate_ticker(db, deposit_data.ticker)

    balance = db.query(Balance).filter_by(user_id=user.id, ticker=instrument.ticker).first()
    if not balance:
        balance = Balance(user_id=user.id, ticker=instrument.ticker, amount=0)
        db.add(balance)

    balance.amount += deposit_data.amount
    db.commit()
    return Ok

@router_admin_balance.post("/withdraw", response_model=Ok)
def withdraw(withdraw_data: WithdrawRequest,
             current_user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    is_admin(current_user)
    user = validate_user(db, withdraw_data.user_id)
    instrument = validate_ticker(db, withdraw_data.ticker)

    balance = db.query(Balance).filter_by(user_id=user.id, ticker=instrument.ticker).first()
    if not balance or (balance.amount-balance.frozen_amount) < withdraw_data.amount:
        raise CustomAPIException(loc=["body", "amount"],
                                 msg=f"Not enough tickers {instrument.ticker}",
                                 type_error=ErrorType.NOT_ENOUGH_FOR_WITHDRAW)

    balance.amount -= withdraw_data.amount
    db.commit()
    return Ok