"""Workspace service for business logic."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workspace import Workspace, Membership, Tenant
from app.models.user import User
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService:
    """Service for workspace operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, workspace_id: UUID) -> Optional[Workspace]:
        """Get workspace by ID."""
        result = await self.db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_slug(self, slug: str) -> Optional[Workspace]:
        """Get workspace by slug."""
        result = await self.db.execute(
            select(Workspace).where(Workspace.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def get_user_workspaces(self, user_id: UUID) -> List[Workspace]:
        """Get all workspaces for a user."""
        result = await self.db.execute(
            select(Workspace)
            .join(Membership)
            .where(Membership.user_id == user_id)
            .options(selectinload(Workspace.memberships))
        )
        return list(result.scalars().all())
    
    async def create(self, data: WorkspaceCreate, user: User) -> Workspace:
        """Create a new workspace with default tenant."""
        # Create tenant
        tenant = Tenant(name=data.name)
        self.db.add(tenant)
        await self.db.flush()
        
        # Create workspace
        workspace = Workspace(
            tenant_id=tenant.id,
            name=data.name,
            slug=data.slug,
            research_opt_in=data.research_opt_in,
        )
        self.db.add(workspace)
        await self.db.flush()
        
        # Add user as admin
        membership = Membership(
            user_id=user.id,
            workspace_id=workspace.id,
            role="admin",
        )
        self.db.add(membership)
        
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace
    
    async def update(self, workspace: Workspace, data: WorkspaceUpdate) -> Workspace:
        """Update a workspace."""
        if data.name is not None:
            workspace.name = data.name
        if data.settings is not None:
            workspace.settings = data.settings
        if data.research_opt_in is not None:
            workspace.research_opt_in = data.research_opt_in
        
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace
    
    async def add_member(
        self,
        workspace: Workspace,
        user: User,
        role: str,
        invited_by: UUID,
    ) -> Membership:
        """Add a member to a workspace."""
        membership = Membership(
            user_id=user.id,
            workspace_id=workspace.id,
            role=role,
            invited_by=invited_by,
        )
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        return membership
    
    async def get_membership(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Optional[Membership]:
        """Get membership for a user in a workspace."""
        result = await self.db.execute(
            select(Membership)
            .where(
                Membership.workspace_id == workspace_id,
                Membership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_members(self, workspace_id: UUID) -> List[Membership]:
        """Get all members of a workspace."""
        result = await self.db.execute(
            select(Membership)
            .where(Membership.workspace_id == workspace_id)
            .options(selectinload(Membership.user))
        )
        return list(result.scalars().all())
    
    async def create_default_workspace(self, user: User) -> Workspace:
        """Create a default workspace for a new user."""
        import re
        
        # Generate slug from email
        email_name = user.email.split("@")[0]
        slug = re.sub(r"[^a-z0-9]", "-", email_name.lower())[:30]
        
        # Make slug unique
        base_slug = slug
        counter = 1
        while await self.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create tenant
        tenant = Tenant(name=f"{user.full_name or email_name}的工作空间")
        self.db.add(tenant)
        await self.db.flush()
        
        # Create workspace
        workspace = Workspace(
            tenant_id=tenant.id,
            name=f"{user.full_name or email_name}的工作空间",
            slug=slug,
            research_opt_in=False,
        )
        self.db.add(workspace)
        await self.db.flush()
        
        # Add user as admin
        membership = Membership(
            user_id=user.id,
            workspace_id=workspace.id,
            role="admin",
        )
        self.db.add(membership)
        
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace
    
    async def get_default_workspace(self, user_id: UUID) -> Optional[Workspace]:
        """Get the default workspace for a user (first one they belong to)."""
        result = await self.db.execute(
            select(Workspace)
            .join(Membership)
            .where(Membership.user_id == user_id)
            .order_by(Membership.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()
