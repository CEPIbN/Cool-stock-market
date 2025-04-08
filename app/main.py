from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db import Base, engine
from app.routers.public import public
from app.db import get_db

app = FastAPI()

app.include_router(public.router)

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    db.commit()
    html_content = "<h2>Hello from FastAPI!</h2>"
    return HTMLResponse(content=html_content)


