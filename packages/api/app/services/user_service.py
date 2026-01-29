"""User service for business logic."""
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for user operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: Union[UUID, str]) -> Optional[User]:
        """Get user by ID."""
        # Convert string to UUID if needed (required for SQLite)
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def create(self, data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            # 用户画像字段
            company_name=data.company_name,
            industry=data.industry,
            region=data.region or "cn",
            business_role=data.business_role,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update(self, user: User, data: UserUpdate) -> User:
        """Update a user."""
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.password is not None:
            user.hashed_password = hash_password(data.password)
        # 用户画像字段
        if data.company_name is not None:
            user.company_name = data.company_name
        if data.industry is not None:
            user.industry = data.industry
        if data.region is not None:
            user.region = data.region
        if data.business_role is not None:
            user.business_role = data.business_role
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = await self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    async def delete(self, user: User) -> None:
        """Delete a user."""
        await self.db.delete(user)
        await self.db.commit()
    
    async def update_password(self, user: User, new_password: str) -> User:
        """Update user's password."""
        user.hashed_password = hash_password(new_password)
        await self.db.commit()
        await self.db.refresh(user)
        return user
