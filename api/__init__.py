from fastapi import APIRouter

from .routers import users
from .routers import trips

# 创建主 API 路由器，包含所有子路由器
api_router = APIRouter(prefix="/api/v1")

# 包含用户路由器
api_router.include_router(users.router)

# 包含旅行路由器
api_router.include_router(trips.router, tags=["Trips"])
# api_router.include_router(expenses.router)
# api_router.include_router(settlements.router)
