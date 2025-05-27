from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

# 数据库和模型导入
from database import engine, get_db
import models  # 导入所有模型以便创建表

# API路由导入
from api import api_router

# 创建所有表（生产环境通常使用Alembic进行迁移）
models.user_models.Base.metadata.create_all(bind=engine)

# 创建FastAPI实例
app = FastAPI(
    title="旅游分账App API",
    description="Travel Expense Splitting App API",
    version="0.1.0",
)

# 包含 API 路由
app.include_router(api_router)

# 根路由
@app.get("/")
async def root():
    return {"message": "Welcome to Travel Expense Splitting App API"}

# 测试数据库连接的端点
@app.get("/test-db/")
def test_db_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"message": "Database connection successful!"}
    except Exception as e:
        return {"message": f"Database connection failed: {str(e)}"}