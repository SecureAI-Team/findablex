"""Calibration error detection routes."""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models.user import User
from app.models.calibration import CalibrationDictionary, CalibrationError
from app.services.project_service import ProjectService
from app.services.workspace_service import WorkspaceService
from app.services.calibration_service import CalibrationChecker, run_calibration_check

router = APIRouter()


# ========== Schemas ==========

class DictionaryCreate(BaseModel):
    """Schema for creating a calibration dictionary entry."""
    dict_type: str = Field(..., description="类型: brand, product, data, competitor")
    correct_value: str = Field(..., description="正确的值")
    error_variants: List[str] = Field(default=[], description="错误表述列表")
    context: Optional[str] = None


class DictionaryResponse(BaseModel):
    """Schema for dictionary response."""
    id: UUID
    project_id: UUID
    dict_type: str
    correct_value: str
    error_variants: List[str]
    context: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True


class CalibrationErrorResponse(BaseModel):
    """Schema for calibration error response."""
    id: UUID
    crawl_result_id: UUID
    project_id: UUID
    error_type: str
    severity: str
    original_text: str
    correct_text: Optional[str]
    explanation: Optional[str]
    context: Optional[str]
    detection_method: str
    review_status: str
    reviewed_by: Optional[UUID]
    review_notes: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


class ReviewUpdate(BaseModel):
    """Schema for updating review status."""
    status: str = Field(..., description="状态: confirmed, dismissed, fixed")
    notes: Optional[str] = None


class CalibrationSummary(BaseModel):
    """Schema for calibration summary."""
    total_errors: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    pending_review: int
    confirmed: int
    dismissed: int


# ========== Dictionary Endpoints ==========

@router.post("/{project_id}/dictionaries", response_model=DictionaryResponse)
async def create_dictionary(
    project_id: UUID,
    data: DictionaryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalibrationDictionary:
    """Add a new calibration dictionary entry for a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    dictionary = CalibrationDictionary(
        project_id=project_id,
        dict_type=data.dict_type,
        correct_value=data.correct_value,
        error_variants=data.error_variants,
        context=data.context,
    )
    
    db.add(dictionary)
    await db.commit()
    await db.refresh(dictionary)
    
    return dictionary


@router.get("/{project_id}/dictionaries", response_model=List[DictionaryResponse])
async def list_dictionaries(
    project_id: UUID,
    dict_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CalibrationDictionary]:
    """List all calibration dictionaries for a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    query = select(CalibrationDictionary).where(
        CalibrationDictionary.project_id == project_id
    )
    
    if dict_type:
        query = query.where(CalibrationDictionary.dict_type == dict_type)
    
    result = await db.execute(query)
    return list(result.scalars().all())


@router.delete("/{project_id}/dictionaries/{dictionary_id}")
async def delete_dictionary(
    project_id: UUID,
    dictionary_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a calibration dictionary entry."""
    result = await db.execute(
        select(CalibrationDictionary)
        .where(CalibrationDictionary.id == dictionary_id)
        .where(CalibrationDictionary.project_id == project_id)
    )
    dictionary = result.scalar_one_or_none()
    
    if not dictionary:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    
    await db.delete(dictionary)
    await db.commit()
    
    return {"message": "Deleted"}


# ========== Error Detection Endpoints ==========

@router.post("/{project_id}/check")
async def run_check(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Run calibration check on all crawl results for a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    result = await run_calibration_check(db, project_id)
    return result


@router.get("/{project_id}/errors", response_model=List[CalibrationErrorResponse])
async def list_errors(
    project_id: UUID,
    severity: Optional[str] = None,
    review_status: Optional[str] = None,
    error_type: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """List calibration errors for a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    query = select(CalibrationError).where(
        CalibrationError.project_id == project_id
    )
    
    if severity:
        query = query.where(CalibrationError.severity == severity)
    if review_status:
        query = query.where(CalibrationError.review_status == review_status)
    if error_type:
        query = query.where(CalibrationError.error_type == error_type)
    
    query = query.order_by(CalibrationError.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    errors = list(result.scalars().all())
    
    return [
        {
            **error.__dict__,
            "created_at": error.created_at.isoformat() if error.created_at else None,
        }
        for error in errors
    ]


@router.get("/{project_id}/errors/summary", response_model=CalibrationSummary)
async def get_error_summary(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalibrationSummary:
    """Get summary of calibration errors for a project."""
    project_service = ProjectService(db)
    workspace_service = WorkspaceService(db)
    
    project = await project_service.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await workspace_service.get_membership(project.workspace_id, current_user.id)
    if not membership and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Total errors
    total_result = await db.execute(
        select(func.count(CalibrationError.id))
        .where(CalibrationError.project_id == project_id)
    )
    total_errors = total_result.scalar() or 0
    
    # By severity
    severity_result = await db.execute(
        select(CalibrationError.severity, func.count(CalibrationError.id))
        .where(CalibrationError.project_id == project_id)
        .group_by(CalibrationError.severity)
    )
    by_severity = dict(severity_result.all())
    
    # By type
    type_result = await db.execute(
        select(CalibrationError.error_type, func.count(CalibrationError.id))
        .where(CalibrationError.project_id == project_id)
        .group_by(CalibrationError.error_type)
    )
    by_type = dict(type_result.all())
    
    # By review status
    status_result = await db.execute(
        select(CalibrationError.review_status, func.count(CalibrationError.id))
        .where(CalibrationError.project_id == project_id)
        .group_by(CalibrationError.review_status)
    )
    status_counts = dict(status_result.all())
    
    return CalibrationSummary(
        total_errors=total_errors,
        by_severity=by_severity,
        by_type=by_type,
        pending_review=status_counts.get("pending", 0),
        confirmed=status_counts.get("confirmed", 0),
        dismissed=status_counts.get("dismissed", 0),
    )


@router.put("/{project_id}/errors/{error_id}/review")
async def update_error_review(
    project_id: UUID,
    error_id: UUID,
    data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Update the review status of a calibration error."""
    result = await db.execute(
        select(CalibrationError)
        .where(CalibrationError.id == error_id)
        .where(CalibrationError.project_id == project_id)
    )
    error = result.scalar_one_or_none()
    
    if not error:
        raise HTTPException(status_code=404, detail="Error not found")
    
    checker = CalibrationChecker(db)
    updated_error = await checker.update_review_status(
        error_id=error_id,
        status=data.status,
        reviewer_id=current_user.id,
        notes=data.notes,
    )
    
    return {
        "id": str(updated_error.id),
        "review_status": updated_error.review_status,
        "reviewed_at": updated_error.reviewed_at.isoformat() if updated_error.reviewed_at else None,
        "message": "Review status updated",
    }
