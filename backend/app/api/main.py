from fastapi import APIRouter

from app.api.routes import items, login, users, utils, mri, crr

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(mri.router, prefix="/mri", tags=["mri"])
api_router.include_router(crr.router, prefix="/crr", tags=["crr"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(items.router, prefix="/items", tags=["items"])
