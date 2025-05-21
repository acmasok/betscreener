from forkscan.api.routes.auth import router as auth_router
from fastapi import FastAPI
from forkscan.api.routes.promocode import router as promocode_router
app = FastAPI()
app.include_router(auth_router, prefix="/auth")
app.include_router(promocode_router, prefix="/promocode")
