from fastapi import FastAPI
from app.routers.cosmos_router import router as cosmos_router
from app.services.logging_service import logger

logger.info("Starting the application")
app = FastAPI()
app.include_router(cosmos_router)

