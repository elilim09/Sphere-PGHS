from fastapi import FastAPI

from routers import ai, lost, meals

app = FastAPI(title="Sphere-PGHS API")

app.include_router(meals.router, prefix="/meals", tags=["meals"])
app.include_router(lost.router, prefix="/lost", tags=["lost"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])


@app.get("/")
async def root():
    return {"message": "Welcome to Sphere-PGHS API"}
