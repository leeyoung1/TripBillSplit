import os
from typing import Any, Dict, Optional
from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API前缀
    API_V1_STR: str = "/api/v1"
    
    # JWT配置
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
    ALGORITHM: str = "HS256"
    # 60分钟 * 24小时 = 1天
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    SERVER_HOST: str = os.environ.get("SERVER_HOST", "http://localhost:8000")
    
    # 数据库配置
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://root:mysql_zPSQd3@115.190.11.77:3307/trip_bill"
    )
    
    # 邮件服务配置
    MAIL_USERNAME: str = os.environ.get("MAIL_USERNAME", "yeaonaiwohe1212@163.com")
    MAIL_PASSWORD: str = os.environ.get("MAIL_PASSWORD", "EJtHpnPYbqDpLZBS")
    MAIL_FROM: EmailStr = "yeaonaiwohe1212@163.com"
    MAIL_PORT: int = int(os.environ.get("MAIL_PORT", "465"))
    MAIL_SERVER: str = os.environ.get("MAIL_SERVER", "smtp.163.com")
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = True
    MAIL_FROM_NAME: str = os.environ.get("MAIL_FROM_NAME", "旅游分账App")
    MAIL_TEMPLATES_DIR: str = "./templates/email"
    
    # 令牌设置
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1
    
    # 前端URL配置，用于邮件中的链接
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    
    model_config = SettingsConfigDict(case_sensitive=True)

# 创建全局配置实例
settings = Settings() 