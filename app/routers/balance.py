from fastapi import APIRouter, HTTPException

router_balance = APIRouter(
    prefix="/api/v1/balance",
    tags=["balance"]
)

router_admin_balance = APIRouter(
    prefix="/api/v1/admin/balance",
    tags=["admin_balance"]
)

@router_balance.get("/")
def get_balance():
    return

@router_admin_balance.post("/deposit")
def deposit_balance():
    return

@router_admin_balance.post("/deposit")
def withdraw_balance():
    return