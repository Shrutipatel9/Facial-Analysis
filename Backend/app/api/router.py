from fastapi import APIRouter

from app.api.routers.auth import router as auth_router
from app.api.routers.photos import router as photos_router
from app.api.routers.questionnaire import router as questionnaire_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(questionnaire_router)
api_router.include_router(photos_router)
