from fastapi import APIRouter

from app.api.routers.ai_visuals import router as ai_visuals_router
from app.api.routers.analysis import router as analysis_router
from app.api.routers.auth import router as auth_router
from app.api.routers.chat import router as chat_router
from app.api.routers.payments import router as payments_router
from app.api.routers.photos import router as photos_router
from app.api.routers.questionnaire import router as questionnaire_router
from app.api.routers.reports import router as reports_router
from app.api.routers.support import router as support_router
from app.api.routers.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(questionnaire_router)
api_router.include_router(photos_router)
api_router.include_router(analysis_router)
api_router.include_router(reports_router)
api_router.include_router(payments_router)
api_router.include_router(ai_visuals_router)
api_router.include_router(chat_router)
api_router.include_router(support_router)
