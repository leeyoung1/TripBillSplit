from datetime import date, datetime
import secrets
from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Body
from sqlalchemy.orm import Session

from api import deps
from models.user import models as user_models
from models.trip import crud as trip_crud
from models.trip import models as trip_models
from models.trip import schemas as trip_schemas

router = APIRouter(prefix="/trips")

# API 端点将在此处实现
@router.post(
    "/create",
    response_model=trip_schemas.TripPublicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建旅游行程",
    description="创建一个新的旅游行程，当前用户自动成为行程所有者。",
)
async def create_trip(
    *,
    db: Session = Depends(deps.get_db_transaction),
    trip_in: trip_schemas.TripCreateRequest,
    current_user: user_models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    创建一个新的旅游行程。
    创建者自动成为行程所有者。
    行程的初始状态将根据其开始日期计算。
    """
    # 验证日期：start_date 必须在 end_date 之前
    if trip_in.start_date >= trip_in.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="行程开始日期必须早于结束日期。",
        )

    # 验证日期：start_date 不能是过去的日期（可选，但建议这样做）
    # 目前，为了灵活性，我们允许过去的 start_date，状态将会被计算。
    if trip_in.start_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="行程开始日期不能是过去的日期，请检查行程日期。",
        )

    created_trip = trip_crud.create_trip(db=db, trip_in=trip_in, creator_id=current_user.user_id)
    if not created_trip:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # 或更具体的错误
            detail="创建行程失败。",
        )
    
    return created_trip
@router.get(
    "/list",
    response_model=trip_schemas.PaginatedTripListResponse,
    summary="获取当前用户的行程列表",
    description="获取当前用户参与的行程列表，支持按状态和角色过滤。",
)
async def get_my_trips(
    *,
    db: Session = Depends(deps.get_db),
    current_user: user_models.User = Depends(deps.get_current_active_user),
    status_filter: int = Query(None, alias="status", description="按行程状态筛选 (1=计划中, 2=进行中, 3=已结束, 4=已取消)"),
    role_filter: int = Query(None, alias="role", description="按用户在行程中的角色筛选 (1=所有者, 2=管理员, 3=成员)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页项目数"),
) -> Any:
    """
    获取当前用户参与的行程列表。
    支持分页，按行程状态和用户在行程中的角色过滤。
    每个行程的状态是动态计算的。如果计算出的状态与存储的状态不同（且不是'已取消'），则存储的状态被更新。
    """
    skip = (page - 1) * page_size
    trips_data = trip_crud.get_trips_by_user(
        db,
        user_id=current_user.user_id,
        skip=skip,
        limit=page_size,
        status=status_filter,
        role=role_filter
    )
    if not trips_data or not trips_data[0]:
        return trip_schemas.PaginatedTripListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            total_pages=0
        )
    updated_trips = []
    current_time = datetime.now() # 确保所有计算使用一致的时间

    for trip in trips_data[0]: # trips_data是包含行程列表和总数的元组
        
        original_db_status = trip.status
        actual_status = deps.calculate_trip_actual_status(trip, current_time)

        # 惰性更新
        if original_db_status != actual_status:
            update_data = trip_schemas.TripUpdateInternalStatus(status=actual_status)
            trip_crud.update_trip_status(db=db, trip_obj=trip, trip_in_status=update_data)
            db.refresh(trip)

        trip.status = actual_status
        updated_trips.append(trip)

    return trip_schemas.PaginatedTripListResponse(
        items=updated_trips,
        total=trips_data[1],
        page=page,
        page_size=page_size,
        total_pages=(trips_data[1] + page_size - 1) // page_size  # 计算总页数，向上取整
    )
@router.get(
    "/detail/{trip_id}",
    response_model=trip_schemas.TripPublicResponse,
    summary="获取特定行程的详细信息",
    description="获取特定行程的详细信息，如果当前用户是活跃成员。",
)
async def get_trip_details(
    *,
    db: Session = Depends(deps.get_db),
    # current_user: user_models.User = Depends(deps.get_current_active_user), # 已由 get_trip_for_member_access 处理
    trip: trip_models.Trip = Depends(deps.get_trip_for_member_access), # 此依赖项处理行程获取和身份验证
) -> Any:
    """
    获取特定行程的详细信息。
    用户必须是该行程的活跃成员。
    行程的状态是动态计算的。如果计算出的状态与存储的状态不同（且不是"已取消"状态），则会更新数据库中存储的状态。
    """
    current_time = datetime.now()
    original_db_status = trip.status
    actual_status = deps.calculate_trip_actual_status(trip, current_time)

    # 惰性更新
    if original_db_status != actual_status and original_db_status != trip_models.TripStatus.CANCELLED.value:
        update_data = trip_schemas.TripUpdateInternalStatus(status=actual_status)
        trip_crud.update_trip_status(db=db, trip_obj=trip, trip_in_status=update_data)
        db.refresh(trip) # 刷新以获取更新后的行程对象

    # 确保响应反映计算出的状态
    trip.status = actual_status
    
    return trip
@router.patch(
    "/update/{trip_id}",
    response_model=trip_schemas.TripPublicResponse,
    summary="更新特定行程",
    description="更新特定行程的详细信息。需要'所有者'或'管理员'角色。",
)
async def update_trip_details(
    *,
    db: Session = Depends(deps.get_db),
    trip_update_data: trip_schemas.TripUpdateRequest,
    current_user: user_models.User = Depends(deps.get_current_active_user), # crud.update_trip 需要
    trip_to_update: trip_models.Trip = Depends(deps.get_trip_for_update_permission), # 处理身份验证并获取行程
) -> Any:
    """
    更新特定行程。
    - 用户必须是行程的所有者或管理员。
    - 状态管理：
        - 如果更新中包含'状态'且为'已取消'，则应用。
        - 如果更新中包含'状态'且不为'已取消'，则忽略并根据日期重新计算。
        - 如果更新中不包含'状态'，但日期发生变化，则状态重新计算（除非当前状态为'已取消'）。
    """
    update_data_dict = trip_update_data.model_dump(exclude_unset=True)
    
    # 如果日期正在更新，则进行日期验证
    new_start_date = update_data_dict.get("start_date", trip_to_update.start_date)
    new_end_date = update_data_dict.get("end_date", trip_to_update.end_date)

    if new_start_date >= new_end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="行程开始日期必须早于结束日期。",
        )

    recalculate_status_due_to_date_change = False
    if "start_date" in update_data_dict or "end_date" in update_data_dict:
        recalculate_status_due_to_date_change = True

    requested_status = update_data_dict.get("status")
    # 如果请求中包含状态，并且也包含日期，则要校验状态
    if requested_status is not None and recalculate_status_due_to_date_change:
        if requested_status == trip_models.TripStatus.CANCELLED.value:
            # 允许显式取消
            update_data_dict["status"] = trip_models.TripStatus.CANCELLED.value
        else:
            temp_trip_for_status_calc = trip_to_update.model_copy(
                update={"start_date": new_start_date, "end_date": new_end_date}
            )
            actual_status = deps.calculate_trip_actual_status(temp_trip_for_status_calc, current_time=datetime.now())
            if actual_status != requested_status:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"行程状态与日期不匹配，请检查行程状态" + \
                        f"修改的日期: {new_start_date} - {new_end_date}, 修改的状态: {requested_status}",
                )

    updated_trip = trip_crud.update_trip(
        db=db,
        db_obj=trip_to_update,
        obj_in=trip_schemas.TripUpdateRequest(**update_data_dict) # 传递处理后的字典
    )
    if not updated_trip:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新行程失败",
        )    
    
    return updated_trip
@router.delete(
    "/delete/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除特定行程（软删除）",
    description="逻辑删除特定行程。需要'所有者'角色。",
)
async def delete_trip_endpoint(
    *,
    db: Session = Depends(deps.get_db),
    current_user: user_models.User = Depends(deps.get_current_active_user), # crud.delete_trip 需要
    trip_to_delete: trip_models.Trip = Depends(deps.get_trip_for_delete_permission), # 处理身份验证并获取行程
) -> None:
    """
    逻辑删除行程。
    只有行程所有者可以执行此操作。
    行程被标记为已删除，但不会从数据库中物理删除。
    """
    success = trip_crud.delete_trip(db=db, db_obj=trip_to_delete)
    if not success:
        # 如果依赖项检查了权限和行程存在性，则这种情况理想情况下应该很少见。
        # 这可能表明软删除机制本身存在问题。
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除行程失败",
        )
    return None # FastAPI 会自动处理 204 No Content 响应
@router.post(
    "/invitation-tokens/{trip_id}",
    response_model=trip_schemas.InvitationTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建行程邀请令牌",
    description="创建行程邀请令牌。需要'所有者'或'管理员'角色。",
)
async def create_trip_invitation_token(
    *,
    db: Session = Depends(deps.get_db),
    token_create_request: trip_schemas.InvitationTokenCreateRequest,
    current_user: user_models.User = Depends(deps.get_current_active_user),
    trip: trip_models.Trip = Depends(deps.get_trip_for_invitation_creation_permission),
    _: None = Depends(deps.trip_is_invitable),
) -> Any:
    """
    创建行程邀请令牌。
    - 用户必须是行程所有者、管理员、编辑或成员。
    - 行程必须处于允许新成员的状态（例如，未取消或已结束，尽管`calculate_trip_actual_status`可能在邀请之前隐式处理）。
      `get_trip_for_invitation_creation_permission` 应确保行程处于"可邀请"状态。
      目前，我们假设依赖项处理基本行程有效性。目前，我们假设依赖项处理基本行程有效性。
    """
    current_time = datetime.now()
    actual_trip_status = deps.calculate_trip_actual_status(trip, current_time)
    if actual_trip_status == trip_models.TripStatus.ENDED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="行程已结束，无法创建邀请。",
        )
    if actual_trip_status == trip_models.TripStatus.CANCELLED.value: # trip.status 也应反映这一点
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="行程已取消，无法创建邀请。",
        )
    
    # 如果提供，确保 max_uses 是正数
    if token_create_request.max_uses is not None and token_create_request.max_uses <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邀请令牌的最大使用次数必须为正整数。",
        )
    # token 要后端生成
    token = secrets.token_urlsafe(32)
    invitation_token = trip_crud.create_trip_invitation(
        db=db,
        trip_id=trip.id,
        creator_id=current_user.user_id,
        invitation_in=token_create_request,
        token=token
    )
    if not invitation_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成邀请令牌失败",
        )
    
    from core.config import settings
    invitation_link = f"{settings.SERVER_HOST}/api/v1/trips/join-trip?token={invitation_token.token}"
    qr_code_data = f"https://api.qrserver.com/v1/create-qr-code/?data={invitation_link}&size=200x200"

    return trip_schemas.InvitationTokenResponse(
        invite_token=invitation_token.token,
        join_link=invitation_link,
        qr_code_data=qr_code_data
    )
# 此端点与 /trips/{trip_id}/... 结构分开
# 但在逻辑上与行程相关。
@router.get(
    "/join-trip",
    response_model=trip_schemas.TripMemberPublicResponse,
    summary="通过邀请令牌加入行程",
    description="通过提供有效的邀请令牌加入行程。",
)
async def join_trip_with_token(
    *,
    db: Session = Depends(deps.get_db),
    token: str = Query(..., description="邀请令牌"),
    current_user: user_models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    通过邀请令牌加入行程。
    - 验证令牌。
    - 检查用户是否已加入行程。
    - 将用户添加到行程，并根据令牌中的角色。
    - 更新令牌使用。
    """
    try:
        trip_member = trip_crud.join_trip_with_invitation_token(
            db=db,
            token_str=token,
            user_id=current_user.user_id
        )
        return trip_member
    except ValueError as e: # 从 CRUD 捕获特定错误
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except LookupError as e: # 例如，未找到令牌
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e: # 例如，用户已经是成员，或者行程不可加入
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, # 如果是权限问题而不是状态冲突，则为 403
            detail=str(e)
        )
    except Exception as e: # 捕获加入过程中其他意外问题
        # 在服务器端记录此异常
        # logger.error(f"加入行程时出现意外错误，令牌：{e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="加入行程时出现意外错误",
        )