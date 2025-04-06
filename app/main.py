from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.db import Base, engine
from app.models import models

#Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    html_content = "<h2>Hello from FastAPI!</h2>"
    return HTMLResponse(content=html_content)

@app.get("/{item}")
def read_root_item(item: int):
    html_content = f"<h2>Ты ввел {item} в path</h2>"
    return HTMLResponse(content=html_content)
