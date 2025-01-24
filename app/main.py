from fastapi import FastAPI
from app.routers.cosmos_router import router as cosmos_router

app = FastAPI()
app.include_router(cosmos_router)