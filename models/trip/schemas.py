from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

# Base models for common fields
class TripBase(BaseModel):
    name: str = Field(..., example="日本东京7日游")
    description: Optional[str] = Field(None, example="旅行的详细描述")
    start_date: date = Field(..., example="2024-08-15")
    end_date: Optional[date] = Field(None, example="2024-08-22")
    budget: Optional[float] = Field(None, example=10000.00)
    cover_image_url: Optional[str] = Field(None, example="https://example.com/cover.jpg")

class TripCreateRequest(TripBase):
    pass

class TripPublicResponse(TripBase):
    id: int
    status: int # TINYINT, e.g., 1 for 'planned', 2 for 'active'
    creator_id: int
    created_at: datetime
    updated_at: datetime
    deleted: bool

    class Config:
        # orm_mode = True # Pydantic V1 orm_mode
        from_attributes = True # Pydantic V2

class TripInListResponse(TripPublicResponse): # For PaginatedTripListResponse
    user_role_in_trip: Optional[int] = None # As per documentation

class PaginatedTripListResponse(BaseModel):
    items: List[TripInListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class TripUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, example="日本东京7日游（更新）")
    description: Optional[str] = Field(None, example="更新后的旅行详细描述")
    start_date: Optional[date] = Field(None, example="2024-08-16")
    end_date: Optional[date] = Field(None, example="2024-08-23")
    budget: Optional[float] = Field(None, example=12000.00)
    cover_image_url: Optional[str] = Field(None, example="https://example.com/new_cover.jpg")
    status: Optional[int] = Field(None, example=4) # e.g., 4 for 'cancelled'

# 用于内部状态更新的简化模式
class TripUpdateInternalStatus(BaseModel):
    """内部使用的旅行状态更新模式，仅包含状态字段"""
    status: int = Field(..., example=2, description="旅行状态: 1=planned, 2=active, 3=ended, 4=cancelled")

# Invitation Schemas
class InvitationTokenCreateRequest(BaseModel):
    expires_in_minutes: Optional[int] = Field(1440, example=1440) # Default 24 hours
    max_uses: Optional[int] = Field(1, example=1) # Default 1 use
    role_to_assign: Optional[int] = Field(4, example=4) # Default 'member'

class InvitationTokenResponse(BaseModel):
    invite_token: str
    join_link: str
    qr_code_data: str
    expires_at: Optional[datetime] = None

class JoinTripWithTokenRequest(BaseModel):
    invite_token: str = Field(..., example="UNIQUE_TOKEN_STRING")

# Trip Member Schemas
class TripMemberBase(BaseModel):
    trip_id: int
    user_id: int
    role: int # TINYINT: 1:owner, 2:admin, 3:editor, 4:member
    status: int # TINYINT: 1:active, 2:invited, 3:pending_owner_approval

class TripMemberPublicResponse(TripMemberBase):
    id: int
    joined_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    deleted: bool

    class Config:
        # orm_mode = True
        from_attributes = True # Pydantic V2

# 根据文档 "JoinTripWithTokenRequest" 的成功响应可以是 TripMemberPublicResponse 或 TripPublicResponse
# 这里我们已经定义了 TripMemberPublicResponse。如果需要返回 TripPublicResponse，调用方可以选择。