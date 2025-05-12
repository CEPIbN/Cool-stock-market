from typing import Optional

from fastapi.params import Header
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.exceptions import CustomAPIException
from app.models.enums.ErrorType import ErrorType
from app.models.models import User


def get_current_user_from_token(
        authorization: Optional[str] = Header(None, title="Authorization"),
        db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("TOKEN "):
        raise CustomAPIException(loc=["header", "authorization"],
                                 msg="Invalid or missing Authorization header",
                                 type_error=ErrorType.AUTHORIZATION)

    api_key = authorization.removeprefix("TOKEN ").strip()

    user = db.query(User).filter_by(api_key=api_key).first()
    if not user:
        raise CustomAPIException(loc=["header", "authorization"],
                                 msg="Invalid API token",
                                 type_error=ErrorType.AUTHORIZATION)

    return user