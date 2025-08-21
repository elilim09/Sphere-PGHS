from fastapi import FastAPI

from routers import bob, ai
from routers import ai

app = FastAPI()

app.include_router(bob.router, prefix="/bob", tags=["bob"])
app.include_router(ai.router, prefix="/lost", tags=["lost"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])

@app.get("/")
async def root():
    return {"message": "Welcome to Sphere-PGHS API"}
