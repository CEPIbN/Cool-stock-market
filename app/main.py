from fastapi import FastAPI
from app.v1.routes import router as v1_router

app = FastAPI(title="Versioned FastAPI App")

app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
