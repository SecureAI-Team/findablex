"""Admin settings API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Permission, require_permission
from app.deps import get_current_user, get_db, get_redis
from app.models.user import User
from app.schemas.settings import (
    AllSettingsResponse,
    BulkUpdateRequest,
    BulkUpdateResponse,
    SettingsByCategoryResponse,
    SettingUpdateResult,
    SystemSettingAuditResponse,
    SystemSettingResponse,
    SystemSettingUpdate,
)
from app.services.settings_service import SettingsService, dynamic_settings

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


async def get_settings_service(
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> SettingsService:
    """Get settings service instance."""
    return SettingsService(db, redis)


@router.get(
    "",
    response_model=AllSettingsResponse,
    summary="Get all settings",
    description="Get all system settings grouped by category. Requires super admin.",
)
async def get_all_settings(
    current_user: User = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    service: SettingsService = Depends(get_settings_service),
):
    """Get all system settings grouped by category."""
    grouped = await service.get_all_settings(mask_secrets=True)
    
    categories = []
    total = 0
    for category, settings in grouped.items():
        category_settings = [
            SystemSettingResponse.from_orm_with_mask(s, mask_secrets=True)
            for s in settings
        ]
        categories.append(SettingsByCategoryResponse(
            category=category,
            settings=category_settings,
        ))
        total += len(settings)
    
    return AllSettingsResponse(categories=categories, total=total)


@router.get(
    "/category/{category}",
    response_model=List[SystemSettingResponse],
    summary="Get settings by category",
    description="Get all settings in a specific category.",
)
async def get_settings_by_category(
    category: str,
    current_user: User = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    service: SettingsService = Depends(get_settings_service),
):
    """Get all settings in a category."""
    settings = await service.get_settings_by_category(category, mask_secrets=True)
    return [
        SystemSettingResponse.from_orm_with_mask(s, mask_secrets=True)
        for s in settings
    ]


@router.get(
    "/key/{key:path}",
    response_model=SystemSettingResponse,
    summary="Get setting by key",
    description="Get a single setting by its key.",
)
async def get_setting_by_key(
    key: str,
    current_user: User = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    service: SettingsService = Depends(get_settings_service),
):
    """Get a single setting by key."""
    setting = await service.get_setting(key, decrypt_secrets=False)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )
    return SystemSettingResponse.from_orm_with_mask(setting, mask_secrets=True)


@router.put(
    "/key/{key:path}",
    response_model=SystemSettingResponse,
    summary="Update setting",
    description="Update a single setting value.",
)
async def update_setting(
    key: str,
    update: SystemSettingUpdate,
    current_user: User = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    service: SettingsService = Depends(get_settings_service),
):
    """Update a single setting."""
    try:
        setting = await service.set_setting(key, update.value, current_user.id)
        
        # Update dynamic settings cache
        dynamic_settings.set_cached(key, update.value)
        
        return SystemSettingResponse.from_orm_with_mask(setting, mask_secrets=True)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put(
    "/bulk",
    response_model=BulkUpdateResponse,
    summary="Bulk update settings",
    description="Update multiple settings at once.",
)
async def bulk_update_settings(
    request: BulkUpdateRequest,
    current_user: User = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    service: SettingsService = Depends(get_settings_service),
):
    """Bulk update multiple settings."""
    updates = [{"key": s.key, "value": s.value} for s in request.settings]
    results = await service.bulk_update_settings(updates, current_user.id)
    
    # Update dynamic settings cache for successful updates
    for result in results:
        if result["success"]:
            update = next(u for u in request.settings if u.key == result["key"])
            dynamic_settings.set_cached(result["key"], update.value)
    
    return BulkUpdateResponse(
        results=[SettingUpdateResult(**r) for r in results],
        success_count=sum(1 for r in results if r["success"]),
        error_count=sum(1 for r in results if not r["success"]),
    )


@router.get(
    "/audit",
    response_model=List[SystemSettingAuditResponse],
    summary="Get settings audit log",
    description="Get audit log of settings changes.",
)
async def get_audit_log(
    key: Optional[str] = Query(None, description="Filter by setting key"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    service: SettingsService = Depends(get_settings_service),
):
    """Get audit log for settings changes."""
    logs = await service.get_audit_log(key=key, limit=limit, offset=offset)
    return [SystemSettingAuditResponse.model_validate(log) for log in logs]


@router.post(
    "/initialize",
    summary="Initialize default settings",
    description="Initialize default settings in the database. Safe to call multiple times.",
)
async def initialize_settings(
    current_user: User = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    service: SettingsService = Depends(get_settings_service),
):
    """Initialize default settings."""
    await service.initialize_default_settings()
    return {"message": "Settings initialized successfully"}


@router.post(
    "/refresh-cache",
    summary="Refresh settings cache",
    description="Refresh the in-memory settings cache from database.",
)
async def refresh_cache(
    current_user: User = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    service: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    """Refresh the settings cache."""
    await dynamic_settings.initialize(db, redis)
    return {"message": "Cache refreshed successfully"}
