from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/order",
    tags=["order"]
)

@router.get("/")
def get_orders():
    return

@router.get("/{order_id}")
def get_order():
    return

@router.post("/")
def create_order():
    return

@router.delete("/")
def delete_order():
    return
