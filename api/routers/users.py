from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlalchemy.orm import Session
from typing import Any

from database import get_db
from models.user import crud, models, schemas
from core.security import (
    create_access_token, 
    create_email_verification_token, 
    verify_email_verification_token,
    create_password_reset_token,
    verify_password_reset_token
)
from api.deps import get_current_user, require_verified_email
from datetime import timedelta
from utils.email import send_verification_email, send_password_reset_email

# 创建路由器，所有路径不需要再带有 "/api/v1" 前缀，因为 api_router 已经有了
router = APIRouter()

# 1. 用户注册
@router.post("/users/register", response_model=schemas.UserPublicResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: schemas.UserCreateRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Any:
    """
    创建新用户
    """
    # 检查邮箱是否已存在
    db_user_by_email = crud.get_user_by_email(db, email=user_data.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该邮箱已被注册"
        )
    
    # 检查手机号是否已存在（如果提供）
    if user_data.phone:
        db_user_by_phone = crud.get_user_by_phone(db, phone=user_data.phone)
        if db_user_by_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该手机号已被注册"
            )
    
    # 创建用户
    user = crud.create_user(db, user_data)
    
    # 生成验证令牌并发送验证邮件
    token = create_email_verification_token(user.user_id)
    await send_verification_email(
        background_tasks=background_tasks,
        email_to=user.email,
        token=token,
        username=user.nickname
    )

    return user

# 2. 用户登录 (OAuth2 表单方式 - 符合 OAuth2 标准)
@router.post("/auth/token", response_model=schemas.TokenDataResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取 JWT 访问令牌 (OAuth2 标准)
    """
    # 验证用户凭证
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=60 * 24)  # 1 day
    access_token = create_access_token(
        data={"sub": user.user_id}, expires_delta=access_token_expires
    )
    
    # 构建响应
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 60 * 60 * 24,  # 1 day in seconds
        "user": {
            "user_id": user.user_id,
            "nickname": user.nickname,
            "email": user.email,
            "is_verified": user.is_verified
        }
    }

# 2.1 用户登录 (JSON方式 - 适合现代前端)
@router.post("/auth/login", response_model=schemas.TokenDataResponse)
async def login_json(
    login_data: schemas.UserLoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    获取 JWT 访问令牌 (JSON格式)
    """
    # 验证用户凭证
    user = crud.authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=60 * 24)  # 1 day
    access_token = create_access_token(
        data={"sub": user.user_id}, expires_delta=access_token_expires
    )
    
    # 构建响应
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 60 * 60 * 24,  # 1 day in seconds
        "user": {
            "user_id": user.user_id,
            "nickname": user.nickname,
            "email": user.email,
            "is_verified": user.is_verified
        }
    }

# 2.2 刷新访问令牌 (Token刷新)
@router.post("/auth/refresh", response_model=schemas.TokenDataResponse)
async def refresh_access_token(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Any:
    """
    刷新 JWT 访问令牌，延长登录状态
    """
    # 创建新的访问令牌
    access_token_expires = timedelta(minutes=60 * 24)  # 1 day
    access_token = create_access_token(
        data={"sub": current_user.user_id}, expires_delta=access_token_expires
    )
    
    # 构建响应
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 60 * 60 * 24,  # 1 day in seconds
        "user": {
            "user_id": current_user.user_id,
            "nickname": current_user.nickname,
            "email": current_user.email,
            "is_verified": current_user.is_verified
        }
    }

# 3. 获取当前用户信息
@router.get("/users/me", response_model=schemas.UserPublicResponse)
async def read_users_me(
    current_user: models.User = Depends(get_current_user)
) -> Any:
    """
    获取当前登录用户的信息
    """
    return current_user

# 4. 更新当前用户信息
@router.patch("/users/me", response_model=schemas.UserPublicResponse)
async def update_user_me(
    user_data: schemas.UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Any:
    """
    更新当前登录用户的信息
    """
    # 检查手机号是否已存在（如果提供）
    if user_data.phone and user_data.phone != current_user.phone:
        db_user_by_phone = crud.get_user_by_phone(db, phone=user_data.phone)
        if db_user_by_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该手机号已被注册"
            )
    
    # 更新用户信息
    updated_data = user_data.model_dump(exclude_unset=True)
    updated_user = crud.update_user(db, current_user, updated_data)
    
    return updated_user

# 5. 修改当前用户密码
@router.put("/users/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: schemas.PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_verified_email)
) -> None:
    """
    修改当前登录用户的密码，要求邮箱已验证
    """
    # 验证当前密码
    if not crud.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前密码错误"
        )
    
    # 修改密码
    crud.change_user_password(db, current_user, password_data.new_password)
    
    return None

# 6. 请求密码重置
@router.post("/auth/password-reset/request", status_code=status.HTTP_200_OK)
async def request_password_reset(
    reset_request: schemas.PasswordResetRequestPayload,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Any:
    """
    请求密码重置，发送重置邮件
    """
    user = crud.get_user_by_email(db, reset_request.email)
    # 即使用户不存在，也返回成功，以防止用户枚举
    if not user:
        return {"message": "如果该邮箱已注册，我们已向其发送了密码重置指导"}
    
    # 生成重置令牌并发送邮件
    token = create_password_reset_token(user.user_id)
    await send_password_reset_email(
        background_tasks=background_tasks,
        email_to=EmailStr(user.email),
        token=token,
        username=user.nickname
    )

    return {"message": "如果该邮箱已注册，我们已向其发送了密码重置指导"}

# 7. 执行密码重置（通过邮件中的令牌）
@router.post("/auth/password-reset/execute", status_code=status.HTTP_200_OK)
async def execute_password_reset(
    reset_data: schemas.PasswordResetExecutePayload,
    db: Session = Depends(get_db)
) -> Any:
    """
    通过令牌执行密码重置
    """
    # 验证重置令牌并获取用户
    user_id = verify_password_reset_token(reset_data.reset_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效或已过期的重置令牌"
        )
    
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效或已过期的重置令牌"
        )
    
    # 重置密码
    crud.change_user_password(db, user, reset_data.new_password)
    
    return {"message": "密码重置成功，请使用新密码登录"}

# 8. 请求邮箱验证
@router.post("/auth/email-verification/request", status_code=status.HTTP_200_OK)
async def request_email_verification(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Any:
    """
    请求重新发送邮箱验证邮件
    """
    # 检查用户邮箱是否已验证
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户邮箱已验证"
        )
    
    # 生成验证令牌并发送邮件
    token = create_email_verification_token(current_user.user_id)
    await send_verification_email(
        background_tasks=background_tasks,
        email_to=EmailStr(current_user.email),
        token=token,
        username=current_user.nickname
    )

    return {"message": "验证邮件已发送，请查收"}

# 9. 执行邮箱验证
@router.post("/auth/email-verification/execute", status_code=status.HTTP_200_OK)
async def execute_email_verification(
    verification_data: schemas.EmailVerificationExecutePayload,
    db: Session = Depends(get_db)
) -> Any:
    """
    通过令牌验证邮箱
    """
    # 验证邮箱验证令牌并获取用户
    user_id = verify_email_verification_token(verification_data.verification_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效或已过期的验证令牌"
        )
    
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效或已过期的验证令牌"
        )
    
    # 设置用户邮箱为已验证
    crud.verify_user_email(db, user)
    
    return {"message": "邮箱验证成功"}

# 这里不实现登出接口，因为JWT通常由客户端删除 