from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"]
)

@router.delete("/user/{user_id}")
def delete_user():
    return

@router.post("/instrument")
def add_instrument():
    return

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
