from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.DTO.Request.NewUser import NewUser
from app.DTO.Response.Ok import Ok
from app.db import get_db
from app.middlewares import get_current_user
from app.models.models import User

router = APIRouter(
    prefix="/api/v1/user",
    tags=["user"]
)

@router.put("/", response_model=Ok)
def update_user(user_data : NewUser,
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    user = db.query(User).get(current_user.id)

    setattr(user, 'name', user_data.name)
    db.commit()

    return Ok

