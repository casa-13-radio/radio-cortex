# api/main.py
from fastapi import FastAPI
from api.routes import health, tracks

app = FastAPI(title="Radio Cortex API", version="0.1.0")

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(tracks.router, prefix="/api/v1", tags=["tracks"])

@app.get("/")
async def root():
    return {"message": "Radio Cortex API"}