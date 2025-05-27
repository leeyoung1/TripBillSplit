from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, Union
import os
import secrets
from .config import settings

# 密码哈希工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置（现在从settings中获取）
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否与哈希值匹配"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希值"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    
    # 确保sub字段是字符串类型
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    
    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 添加到 payload
    to_encode.update({"exp": expire})
    
    # 编码 JWT
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解码并验证 JWT 令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# 生成随机令牌
def generate_random_token() -> str:
    """生成一个随机安全令牌"""
    return secrets.token_urlsafe(32)

# 为邮箱验证创建令牌
def create_email_verification_token(user_id: int) -> str:
    """创建邮箱验证令牌"""
    expires = datetime.utcnow() + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
    data = {
        "sub": str(user_id),
        "exp": expires,
        "type": "email_verification"
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

# 验证邮箱验证令牌
def verify_email_verification_token(token: str) -> Optional[int]:
    """验证邮箱验证令牌，返回用户ID或None"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "email_verification":
            return None
        user_id = int(payload.get("sub"))
        return user_id
    except (JWTError, ValueError):
        return None

# 为密码重置创建令牌
def create_password_reset_token(user_id: int) -> str:
    """创建密码重置令牌"""
    expires = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    data = {
        "sub": str(user_id),
        "exp": expires,
        "type": "password_reset"
    }
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

# 验证密码重置令牌
def verify_password_reset_token(token: str) -> Optional[int]:
    """验证密码重置令牌，返回用户ID或None"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        user_id = int(payload.get("sub"))
        return user_id
    except (JWTError, ValueError):
        return None 