from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session


from app.routers import public, admin, balance, order, user
from app.db import get_db
from app.seed import seed

app = FastAPI()

app.include_router(public.router)
app.include_router(admin.router)
app.include_router(user.router)
app.include_router(order.router)
app.include_router(balance.router_balance)
app.include_router(balance.router_admin_balance)

# @app.on_event("startup")
# def startup_event():
#     Base.metadata.create_all(bind=engine)
#     seed()

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    db.commit()
    html_content = "<h2>Hello from FastAPI!</h2>"
    return HTMLResponse(content=html_content)


