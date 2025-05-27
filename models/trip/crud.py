from typing import Any, Dict, List, Optional, Tuple, cast, Union

from sqlalchemy.orm import Session
from sqlalchemy import or_

from . import models as trip_models
from . import schemas as trip_schemas
from datetime import datetime, date

# Trip CRUD functions
def create_trip(db: Session, *, trip_in: trip_schemas.TripCreateRequest, creator_id: int) -> trip_models.Trip:
    """
    创建新的旅行记录。
    - 根据 start_date 初始化 status。
    - 自动为创建者在 trip_members 表创建记录 (role='owner', status='active')。
    """
    # 状态初始化: 根据 start_date 和当前服务器时间
    # 1:planned, 2:active, 3:ended, 4:cancelled
    current_date = date.today()
    trip_status = trip_models.TripStatus.PLANNED.value if trip_in.start_date > current_date else trip_models.TripStatus.ACTIVE.value

    db_trip = trip_models.Trip(
        name=trip_in.name,
        description=trip_in.description,
        start_date=trip_in.start_date,
        end_date=trip_in.end_date,
        budget=trip_in.budget,
        cover_image_url=trip_in.cover_image_url,
        status=trip_status,
        creator_id=creator_id,
        deleted=False # 显式设置
    )
    db.add(db_trip)
    db.flush() # 需要 trip_id 来创建 TripMember

    # 自动为创建者创建 TripMember 记录
    # role: 1:owner, status: 1:active
    db_trip_member = trip_models.TripMember(
        trip_id=db_trip.id,
        user_id=creator_id,
        role=trip_models.TripMemberRole.OWNER.value, # owner
        status=trip_models.TripMemberStatus.ACTIVE.value, # active
        joined_at=datetime.now(), # 假设立即加入
        deleted=False # 显式设置
    )
    db.add(db_trip_member)
    
    db.commit()
    db.refresh(db_trip)
    return db_trip

def get_trip(db: Session, trip_id: int) -> Optional[trip_models.Trip]:
    """
    根据 ID 获取单个旅行记录 (未逻辑删除的)。
    """
    return db.query(trip_models.Trip).filter(trip_models.Trip.id == trip_id, trip_models.Trip.deleted == False).first()

def get_trips_by_user(db: Session, *, user_id: int, skip: int = 0, limit: int = 10, status: Optional[int] = None, role: Optional[int] = None) -> Tuple[List[trip_models.Trip], int]:
    """
    获取指定用户参与的旅行列表 (分页，可按状态和角色筛选)。
    返回旅行列表和总数。
    注意：此函数主要负责从数据库获取数据，动态状态计算和懒更新的逻辑将在 API 层面处理。
    """
    query = db.query(trip_models.Trip, trip_models.TripMember.role.label('user_role_in_trip'))\
        .join(trip_models.TripMember, trip_models.Trip.id == trip_models.TripMember.trip_id)\
        .filter(trip_models.TripMember.user_id == user_id)\
        .filter(trip_models.Trip.deleted == False)\
        .filter(trip_models.TripMember.deleted == False)\
        .filter(trip_models.TripMember.status == trip_models.TripMemberStatus.ACTIVE.value) # 成员状态为 active

    if status is not None:
        # 注意：文档提到动态状态计算在API层，这里基于数据库存储的status筛选
        query = query.filter(trip_models.Trip.status == status)
    
    if role is not None:
        query = query.filter(trip_models.TripMember.role == role)

    total = query.count()
    
    results = query.order_by(trip_models.Trip.start_date.desc())\
                 .offset(skip)\
                 .limit(limit)\
                 .all()
    
    # 将查询结果转换为Trip对象列表，并设置user_role_in_trip属性
    trips = []
    for trip, role in results:
        setattr(trip, 'user_role_in_trip', role)  # 添加用户角色属性
        trips.append(trip)
        
    return trips, total

def update_trip(db: Session, *, db_obj: trip_models.Trip, obj_in: Union[trip_schemas.TripUpdateRequest, Dict[str, Any]]) -> trip_models.Trip:
    """
    更新旅行信息。
    注意 status 字段的特殊处理逻辑。
    """
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True) # Pydantic V2

    # 更新基础字段
    for field, value in update_data.items():
        if hasattr(db_obj, field):
            setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_trip(db: Session, *, db_obj: trip_models.Trip) -> trip_models.Trip:
    """
    逻辑删除旅行记录。
    需要级联逻辑删除关联的 trip_members。
    其他关联模型 (expenses, expense_splits, settlements) 暂时注释。
    """
    db_obj.deleted = True
    # TODO: 逻辑删除关联的 expenses, expense_splits, settlements
    # 例如:
    # from models import expense_models # 假设存在
    # db.query(expense_models.Expense)\
    #   .filter(expense_models.Expense.trip_id == db_obj.id)\
    #   .update({"deleted": True, "updated_at": datetime.utcnow()})
    # ... 对于 expense_splits 和 settlements 类似

    db.add(db_obj)
    db.commit()
    return db_obj

# TripMember CRUD functions
def create_trip_member(db: Session, *, trip_id: int, user_id: int, role: int, status: int = 1) -> trip_models.TripMember:
    """
    创建旅行成员记录。
    status: 1:active, 2:invited, 3:pending_owner_approval
    role: 1:owner, 2:admin, 3:editor, 4:member
    """
    # 检查是否已存在未删除的记录
    existing_member = db.query(trip_models.TripMember)\
        .filter(trip_models.TripMember.trip_id == trip_id,
                trip_models.TripMember.user_id == user_id,
                trip_models.TripMember.deleted == False)\
        .first()
    
    if existing_member:
        # 如果已存在，可以根据业务逻辑选择更新或抛出异常
        # 这里假设如果存在则更新其 role 和 status，并取消删除标记（如果之前被删了）
        existing_member.role = role
        existing_member.status = status
        existing_member.deleted = False
        if status == 1 and not existing_member.joined_at: # 状态为 active 且之前未记录加入时间
             existing_member.joined_at = datetime.now()
        db_member = existing_member
    else:
        db_member = trip_models.TripMember(
            trip_id=trip_id,
            user_id=user_id,
            role=role,
            status=status,
            joined_at=datetime.now() if status == trip_models.TripMemberStatus.ACTIVE.value else None, # 仅 active 状态记录加入时间
            deleted=False
        )
        db.add(db_member)

    db.commit()
    db.refresh(db_member)
    return db_member

def get_trip_member(db: Session, *, trip_id: int, user_id: int) -> Optional[trip_models.TripMember]:
    """
    获取特定用户在特定旅行中的成员信息 (未逻辑删除的)。
    """
    return db.query(trip_models.TripMember)\
        .filter(trip_models.TripMember.trip_id == trip_id,
                trip_models.TripMember.user_id == user_id,
                trip_models.TripMember.deleted == False)\
        .first()

def get_trip_members_by_trip_id(db: Session, trip_id: int, skip: int = 0, limit: int = 100) -> List[trip_models.TripMember]:
    """
    获取某个旅行的所有成员 (未逻辑删除的)。
    """
    return db.query(trip_models.TripMember)\
        .filter(trip_models.TripMember.trip_id == trip_id, trip_models.TripMember.deleted == False)\
        .order_by(trip_models.TripMember.created_at.asc())\
        .offset(skip)\
        .limit(limit)\
        .all() # type ignore

def update_trip_member_role(db: Session, *, db_obj: trip_models.TripMember, new_role: int) -> trip_models.TripMember:
    """
    更新成员角色。
    role: 1:owner, 2:admin, 3:editor, 4:member
    """
    if db_obj.deleted:
        # 或者可以抛出异常，表示不能修改已删除的成员
        return db_obj # 或者根据业务逻辑决定是否允许操作已删除对象

    db_obj.role = new_role
    # db_obj.updated_at = datetime.utcnow() # onupdate=func.now() 会自动处理
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_trip_member_status(db: Session, *, db_obj: trip_models.TripMember, new_status: int) -> trip_models.TripMember:
    """
    更新成员状态。
    status: 1:active, 2:invited, 3:pending_owner_approval
    """
    if db_obj.deleted:
        return db_obj

    db_obj.status = new_status
    if new_status == 1 and not db_obj.joined_at: # 如果更新为 active 且之前未记录加入时间
        db_obj.joined_at = datetime.now()
    elif new_status != 1: # 如果状态不是 active，理论上 joined_at 可以保留或清空，根据业务需求
        pass # 当前保留 joined_at

    # db_obj.updated_at = datetime.now() # onupdate=func.now() 会自动处理
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_trip_member(db: Session, *, db_obj: trip_models.TripMember) -> trip_models.TripMember:
    """
    逻辑删除旅行成员。
    """
    db_obj.deleted = True
    # db_obj.updated_at = datetime.utcnow() # onupdate=func.now() 会自动处理
    db.add(db_obj)
    db.commit()
    # db.refresh(db_obj) # 对象已标记删除
    return db_obj

# TripInvitation CRUD functions
def create_trip_invitation(db: Session, *, invitation_in: trip_schemas.InvitationTokenCreateRequest, trip_id: int, creator_id: int, token: str) -> trip_models.TripInvitation:
    """
    创建旅行邀请记录。
    """
    from datetime import timedelta

    expires_at = None
    if invitation_in.expires_in_minutes:
        expires_at = datetime.now() + timedelta(minutes=invitation_in.expires_in_minutes)

    db_invitation = trip_models.TripInvitation(
        trip_id=trip_id,
        token=token,
        created_by_user_id=creator_id,
        expires_at=expires_at,
        max_uses=invitation_in.max_uses,
        role_to_assign=invitation_in.role_to_assign,
        current_uses=0,
        is_active=True, # 新创建的邀请默认为 active
        deleted=False
    )
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    return db_invitation

def get_invitation_by_token(db: Session, token: str) -> Optional[trip_models.TripInvitation]:
    """
    根据邀请令牌获取邀请信息 (未逻辑删除且有效的)。
    有效性检查: is_active = True, 未过期, current_uses < max_uses (如果 max_uses 不为 None)
    """
    now = datetime.now()
    query = db.query(trip_models.TripInvitation)\
        .filter(trip_models.TripInvitation.token == token,
                trip_models.TripInvitation.deleted == False,
                trip_models.TripInvitation.is_active == True)
    
    # 检查是否过期
    query = query.filter(or_(
        trip_models.TripInvitation.expires_at == None,
        trip_models.TripInvitation.expires_at > now
    ))

    # 检查使用次数 (如果 max_uses is not None)
    # 这部分检查也可以在服务层做，但既然是 get "有效" invitation，这里加上也合理
    invitation = query.first()
    if invitation:
        if invitation.max_uses is not None and invitation.current_uses >= invitation.max_uses:
            # 即使找到了，如果使用次数已达上限，也视为无效
            # 可以选择在这里将其 is_active 设置为 False
            # invitation.is_active = False
            # db.commit()
            # db.refresh(invitation)
            return None
    return invitation


def increment_invitation_uses(db: Session, *, db_obj: trip_models.TripInvitation) -> trip_models.TripInvitation:
    """
    增加邀请的使用次数，并根据 max_uses 可能停用邀请。
    """
    if db_obj.deleted or not db_obj.is_active:
        # 或者抛出异常，表示不能操作已删除或已停用的邀请
        return db_obj

    db_obj.current_uses += 1
    
    if db_obj.max_uses is not None and db_obj.current_uses >= db_obj.max_uses:
        db_obj.is_active = False
        
    # db_obj.updated_at = datetime.utcnow() # onupdate=func.now() 会自动处理
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_trip_status(db: Session, *, trip_obj: trip_models.Trip, trip_in_status: trip_schemas.TripUpdateInternalStatus) -> trip_models.Trip:
    """
    仅更新旅行状态的简化函数。
    此函数专用于更新旅行的状态字段，通常由系统内部调用，用于动态状态更新。
    """
    # 更新状态
    trip_obj.status = trip_in_status.status
    
    # 保存更新
    db.add(trip_obj)
    db.commit()
    db.refresh(trip_obj)
    return trip_obj
def get_trip_by_id(db: Session, trip_id: int) -> Optional[trip_models.Trip]:
    """
    根据 ID 获取单个旅行记录 (未逻辑删除的)。
    """
    return db.query(trip_models.Trip)\
        .filter(trip_models.Trip.id == trip_id, trip_models.Trip.deleted == False)\
        .first()
def get_trip_member_by_trip_and_user(db: Session, trip_id: int, user_id: int) -> Optional[trip_models.TripMember]:
    """
    获取特定用户在特定旅行中的成员信息 (未逻辑删除的)。
    """
    return db.query(trip_models.TripMember)\
        .filter(trip_models.TripMember.trip_id == trip_id,
                trip_models.TripMember.user_id == user_id,
                trip_models.TripMember.deleted == False)\
        .first()
def join_trip_with_invitation_token(db: Session, *, token_str: str, user_id: int) -> trip_models.TripMember:
    """
    通过邀请令牌加入行程。
    """
    invitation = get_invitation_by_token(db, token_str)
    if not invitation:
        raise ValueError("无效的邀请令牌")
    
    trip_member = get_trip_member_by_trip_and_user(db, invitation.trip_id, user_id)
    if trip_member:
        raise PermissionError("用户已加入行程")
    
    trip_member = create_trip_member(db, trip_id=invitation.trip_id, user_id=user_id, role=invitation.role_to_assign, status=trip_models.TripMemberStatus.ACTIVE.value)
    return trip_member