from sqlalchemy import Column, Integer, String, Text, Date, DECIMAL, ForeignKey, DATETIME, Boolean, func
from sqlalchemy.orm import relationship
from database import Base # 假设 database.py 在项目根目录定义了 Base

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    budget = Column(DECIMAL(10, 2), nullable=True)
    cover_image_url = Column(String(255), nullable=True)
    status = Column(Integer, nullable=False, default=1, comment="旅行状态: 1:planned, 2:active, 3:ended, 4:cancelled") # TINYINT in MySQL
    creator_id = Column(Integer, nullable=False, comment="逻辑关联 users.id") # 假设 users.id 是 Integer

    created_at = Column(DATETIME, nullable=False, server_default=func.now())
    updated_at = Column(DATETIME, nullable=False, server_default=func.now(), onupdate=func.now())
    deleted = Column(Boolean, nullable=False, default=False, comment="逻辑删除标记: FALSE未删除, TRUE已删除")

    # Relationships (如果需要，可以稍后添加)
    # members = relationship("TripMember", back_populates="trip")
    # invitations = relationship("TripInvitation", back_populates="trip")

class TripMember(Base):
    __tablename__ = "trip_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, comment="逻辑关联 trips.id")
    user_id = Column(Integer, nullable=False, comment="逻辑关联 users.id") # 假设 users.id 是 Integer
    role = Column(Integer, nullable=False, comment="成员角色: 1:owner, 2:admin, 3:editor, 4:member") # TINYINT in MySQL
    status = Column(Integer, nullable=False, default=2, comment="成员状态: 1:active, 2:invited, 3:pending_owner_approval") # TINYINT in MySQL
    joined_at = Column(DATETIME, nullable=True, comment="成员实际加入或变为active的时间")

    created_at = Column(DATETIME, nullable=False, server_default=func.now())
    updated_at = Column(DATETIME, nullable=False, server_default=func.now(), onupdate=func.now())
    deleted = Column(Boolean, nullable=False, default=False, comment="逻辑删除标记: FALSE未删除, TRUE已删除")

    # Relationships (如果需要，可以稍后添加)
    # trip = relationship("Trip", back_populates="members")
    # user = relationship("User", back_populates="trips_membership") # 假设 User 模型有 trips_membership

class TripInvitation(Base):
    __tablename__ = "trip_invitations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False, comment="逻辑关联 trips.id")
    token = Column(String(255), nullable=False, unique=True, index=True) # 文档建议应用层保证唯一性，但数据库层面加约束更好
    created_by_user_id = Column(Integer, nullable=False, comment="逻辑关联 users.id") # 假设 users.id 是 Integer
    expires_at = Column(DATETIME, nullable=True)
    max_uses = Column(Integer, nullable=True, default=1)
    current_uses = Column(Integer, nullable=False, default=0)
    role_to_assign = Column(Integer, nullable=False, default=4, comment="例如 4=member") # TINYINT in MySQL

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DATETIME, nullable=False, server_default=func.now())
    updated_at = Column(DATETIME, nullable=False, server_default=func.now(), onupdate=func.now())
    deleted = Column(Boolean, nullable=False, default=False, comment="逻辑删除标记: FALSE未删除, TRUE已删除")

    # Relationships (如果需要，可以稍后添加)
    # trip = relationship("Trip", back_populates="invitations")
    # creator = relationship("User", back_populates="created_invitations") # 假设 User 模型有 created_invitations
import enum

class TripStatus(enum.Enum):
    PLANNED = 1
    ACTIVE = 2
    ENDED = 3
    CANCELLED = 4

class TripRole(enum.Enum):
    OWNER = 1
    ADMIN = 2
    EDITOR = 3
    MEMBER = 4

class TripMemberStatus(enum.Enum):
    ACTIVE = 1
    INVITED = 2
    PENDING_OWNER_APPROVAL = 3

class TripMemberRole(enum.Enum):
    OWNER = 1
    ADMIN = 2
    EDITOR = 3
    MEMBER = 4