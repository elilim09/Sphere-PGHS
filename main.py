from fastapi import FastAPI

from routers import bob, lost
from routers import lost

app = FastAPI()

app.include_router(bob.router, prefix="/bob", tags=["bob"])
app.include_router(lost.router, prefix="/lost", tags=["lost"])
app.include_router(lost.router, prefix="/ai", tags=["ai"])

@app.get("/")
async def root():
    return {"message": "Welcome to Sphere-PGHS API"}
