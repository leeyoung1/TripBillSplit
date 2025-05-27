from pydantic import BaseModel, EmailStr, Field, field_validator, validator
from datetime import datetime
from typing import Optional, List, Dict, Any

# --- User Schemas ---

class UserBase(BaseModel):
    email: EmailStr
    nickname: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)

class UserCreateRequest(UserBase):
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def password_strength(cls, v):
        # 这里可以添加更复杂的密码强度验证逻辑
        if len(v) < 8:
            raise ValueError('密码长度必须至少为8位')
        return v

class UserPublicResponse(UserBase):
    user_id: int
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # Pydantic V2 语法

# 登录请求
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

# 用户信息（用于Token响应）
class UserInfo(BaseModel):
    user_id: int
    nickname: str
    email: EmailStr
    is_verified: bool

# Token响应
class TokenDataResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # 令牌有效期（秒）
    user: UserInfo

# 用户信息更新请求
class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=50)
    avatar_url: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)

# 密码修改请求
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    def password_strength(cls, v, values):
        # 确保新密码与当前密码不同
        if 'current_password' in values and v == values['current_password']:
            raise ValueError('新密码不能与当前密码相同')
        # 这里可以添加更复杂的密码强度验证逻辑
        if len(v) < 8:
            raise ValueError('密码长度必须至少为8位')
        return v

# 密码重置请求
class PasswordResetRequestPayload(BaseModel):
    email: EmailStr

# 密码重置执行
class PasswordResetExecutePayload(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def password_strength(cls, v):
        # 这里可以添加更复杂的密码强度验证逻辑
        if len(v) < 8:
            raise ValueError('密码长度必须至少为8位')
        return v

# 邮箱验证执行
class EmailVerificationExecutePayload(BaseModel):
    verification_token: str 