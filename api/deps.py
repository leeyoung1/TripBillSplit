import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from database import get_db, get_db_transaction
from models.user import crud, models
from core.security import SECRET_KEY, ALGORITHM

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# 获取当前用户
async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    """
    从请求的 OAuth2 令牌中获取当前用户
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 解码 token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"payload: {payload}")
        user_id_str = payload.get("sub")
        if user_id_str is None:
            logger.warning("令牌中未找到用户ID")
            raise credentials_exception
        
        # 将字符串ID转换为整数
        try:
            user_id = int(user_id_str)
            logger.info(f"令牌解码成功，用户ID: {user_id}")
        except ValueError:
            logger.error(f"无法将用户ID转换为整数: {user_id_str}")
            raise credentials_exception
    except JWTError:
        logger.error("令牌解码失败")
        raise credentials_exception
    
    # 从数据库获取用户
    user = crud.get_user_by_id(db, user_id)
    if user is None:
        logger.warning(f"未找到ID为 {user_id} 的用户")
        raise credentials_exception
    if not user.is_active:
        logger.warning(f"用户 {user_id} 未激活")
        raise credentials_exception
    logger.info(f"用户 {user_id} 认证成功")
    return user

# 确保用户邮箱已验证的依赖
async def require_verified_email(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    检查当前用户的邮箱是否已验证
    """
    if not current_user.is_verified:
        logger.warning(f"用户 {current_user.user_id} 邮箱未验证")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户邮箱未验证，请先验证邮箱",
        )
    logger.info(f"用户 {current_user.user_id} 邮箱已验证")
    return current_user

from datetime import datetime, timezone
from fastapi import Path
from models.trip import models as trip_models, crud as trip_crud # Added trip_models and trip_crud
from models.trip.models import TripMemberStatus, TripRole, TripStatus # For enum/int comparison

# 动态状态计算辅助函数
def calculate_trip_actual_status(trip: trip_models.Trip, current_time: datetime = None) -> int:
    """
    根据旅行的 start_date, end_date 和当前时间计算其实际状态。
    如果数据库中存储的 status 是 'cancelled' (4)，则保持为 'cancelled'。
    实际状态 1='planned', 2='active', 3='ended'
    """
    if trip.status == TripStatus.CANCELLED.value: # 4 for cancelled
        return TripStatus.CANCELLED.value

    # 确保current_time不为None
    if current_time is None:
        current_time = datetime.now()
    
    # 将date类型转换为datetime类型，设置为当天的0点
    start_date_aware = datetime.combine(trip.start_date, datetime.min.time())
    end_date_aware = datetime.combine(trip.end_date, datetime.max.time())  # 使用当天的23:59:59.999999

    if current_time < start_date_aware:
        return TripStatus.PLANNED.value # 1 for planned
    elif start_date_aware <= current_time <= end_date_aware:
        return TripStatus.ACTIVE.value # 2 for active
    else:
        return TripStatus.ENDED.value # 3 for ended

# 权限校验依赖项
async def get_trip_for_member_access(
    trip_id: int = Path(..., title="The ID of the trip to retrieve", ge=1),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> trip_models.Trip:
    """
    获取 trip_id 对应的旅行，并校验当前用户是否为该旅行的活跃成员。
    """
    trip = trip_crud.get_trip_by_id(db, trip_id=trip_id)
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到行程")

    member = trip_crud.get_trip_member_by_trip_and_user(db, trip_id=trip_id, user_id=current_user.user_id)
    if not member or member.status != TripMemberStatus.ACTIVE.value: # 1 for active member
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你没有权限访问此行程或不是活跃成员"
        )
    return trip

async def get_trip_for_update_permission(
    trip: trip_models.Trip = Depends(get_trip_for_member_access),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db) # db might be needed if we re-fetch member info
) -> trip_models.Trip:
    """
    校验当前用户是否有权限更新旅行 (owner 或 admin)。
    """
    member = trip_crud.get_trip_member_by_trip_and_user(db, trip_id=trip.id, user_id=current_user.user_id)
    # Member existence and active status is already checked by get_trip_for_member_access
    if not member or member.role not in [TripRole.OWNER.value, TripRole.ADMIN.value]: # 1 for owner, 2 for admin
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to update this trip.")
    return trip

async def get_trip_for_delete_permission(
    trip: trip_models.Trip = Depends(get_trip_for_member_access),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> trip_models.Trip:
    """
    校验当前用户是否有权限删除旅行 (owner)。
    """
    member = trip_crud.get_trip_member_by_trip_and_user(db, trip_id=trip.id, user_id=current_user.user_id)
    if not member or member.role != TripRole.OWNER.value: # 1 for owner
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the trip owner can delete the trip.")
    return trip

async def get_trip_for_invitation_creation_permission(
    trip: trip_models.Trip = Depends(get_trip_for_member_access),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> trip_models.Trip:
    """
    校验当前用户是否有权限创建旅行邀请 (owner, admin, editor, member)。
    """
    member = trip_crud.get_trip_member_by_trip_and_user(db, trip_id=trip.id, user_id=current_user.user_id)
    if not member or member.role not in [TripRole.OWNER.value, TripRole.ADMIN.value, TripRole.EDITOR.value, TripRole.MEMBER.value]: # 1 for owner, 2 for admin, 3 for editor, 4 for member
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only trip owners, admins or editors can create invitations.")
    return trip

async def trip_is_invitable(
    trip: trip_models.Trip = Depends(get_trip_for_member_access),
) -> None:
    """
    校验当前旅行是否处于可邀请状态。
    """
    actual_status = calculate_trip_actual_status(trip, current_time=datetime.now())
    if actual_status == TripStatus.ENDED.value or actual_status == TripStatus.CANCELLED.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="旅行已结束或已取消，无法邀请新成员")

# Alias get_current_active_user for clarity as per requirements
async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户未激活")
    return current_user