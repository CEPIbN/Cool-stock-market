from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/")
def read_root():
    html_content = "<h2>Hello from FastAPI!</h2>"
    return HTMLResponse(content=html_content)

@app.get("/{item}")
def read_root_item(item: int):
    html_content = f"<h2>Ты ввел {item} в path</h2>"
    return HTMLResponse(content=html_content)
