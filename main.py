from fastapi import FastAPI
from routers import users, items, admin

app = FastAPI(title="Sphere-PGHS", version="1.0.0")

# 라우터 등록
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(items.router, prefix="/items", tags=["Items"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

@app.get("/")
def root():
    return {"message": "Sphere-PGHS API 서버 동작 중"}
