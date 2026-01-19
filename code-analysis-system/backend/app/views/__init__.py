from fastapi import APIRouter
from app.views import auth, users, projects

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
