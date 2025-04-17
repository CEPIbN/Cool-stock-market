from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/v1/admin/user",
    tags=["user"]
)

@router.delete("/{user_id}")
def delete_user():
    return

