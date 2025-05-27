from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime
from typing import Optional, Dict, Any

from . import models, schemas
from core.security import get_password_hash, verify_password

# 根据email查找用户
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(
        and_(
            models.User.email == email,
            models.User.deleted == False
        )
    ).first()

# 根据phone查找用户
def get_user_by_phone(db: Session, phone: str) -> Optional[models.User]:
    if not phone:
        return None
    return db.query(models.User).filter(
        and_(
            models.User.phone == phone,
            models.User.deleted == False
        )
    ).first()


# 根据user_id查找用户
def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(
        and_(
            models.User.user_id == user_id,
            models.User.deleted == False
        )
    ).first()

# 创建新用户
def create_user(db: Session, user_data: schemas.UserCreateRequest) -> models.User:
    # 创建用户时对密码进行哈希处理
    hashed_password = get_password_hash(user_data.password)
    db_user = models.User(
        email=user_data.email,
        nickname=user_data.nickname,
        hashed_password=hashed_password,
        phone=user_data.phone,
        is_active=True,
        is_verified=False,  # 默认为未验证状态
        deleted=False,      # 明确设置为未删除状态
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# 更新用户信息
def update_user(db: Session, user: models.User, user_data: Dict[str, Any]) -> models.User:
    for key, value in user_data.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    
    # 更新 updated_at 字段
    user.updated_at = datetime.now()
    
    db.commit()
    db.refresh(user)
    return user

# 修改用户密码
def change_user_password(db: Session, user: models.User, new_password: str) -> models.User:
    user.hashed_password = get_password_hash(new_password)
    user.updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    return user

# 验证用户邮箱
def verify_user_email(db: Session, user: models.User) -> models.User:
    user.is_verified = True
    user.updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    return user

# 逻辑删除用户
def delete_user(db: Session, user: models.User) -> models.User:
    user.deleted = True     # 设置为已删除状态
    user.is_active = False  # 同时也设置为非活动状态
    user.updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    return user

# 验证用户凭证
def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user 