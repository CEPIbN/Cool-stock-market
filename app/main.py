from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.DTO.Response.HTTPValidationError import HTTPValidationError, ValidationErrorDetail
from app.exceptions import custom_http_validation_exception_handler, CustomAPIException
from app.routers import public, admin, balance, order, user
from app.db import get_db

app = FastAPI()

app.include_router(public.router)
app.include_router(admin.router)
app.include_router(user.router)
app.include_router(order.router)
app.include_router(balance.router_balance)
app.include_router(balance.router_admin_balance)

app.add_exception_handler(RequestValidationError, custom_http_validation_exception_handler)

@app.exception_handler(CustomAPIException)
async def unhandled_exception_handler(request: Request, exc: CustomAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content=HTTPValidationError(
            detail=[ValidationErrorDetail(loc=exc.loc,
                                          msg=exc.msg,
                                          type=exc.type)]
        ).model_dump()
    )

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    db.commit()
    html_content = "<h2>Hello from FastAPI!</h2>"
    return HTMLResponse(content=html_content)


