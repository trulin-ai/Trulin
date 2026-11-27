import uuid
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import RecordStatus, UserRole
from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def list_by_organization(self, organization_id: uuid.UUID) -> Sequence[User]:
        stmt = (
            select(User)
            .where(User.organization_id == organization_id, User.status != RecordStatus.DELETED)
            .order_by(User.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_email(self, organization_id: uuid.UUID, email: str) -> User | None:
        stmt = select(User).where(User.organization_id == organization_id, User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        organization_id: uuid.UUID,
        name: str,
        email: str,
        role: UserRole = UserRole.VIEWER,
        title: str | None = None,
        department: str | None = None,
        avatar_url: str | None = None,
        status: RecordStatus = RecordStatus.ACTIVE,
        id: uuid.UUID | None = None,
    ) -> User:
        user = User(
            id=id or uuid.uuid4(),
            organization_id=organization_id,
            name=name,
            email=email,
            role=role,
            title=title,
            department=department,
            avatar_url=avatar_url,
            status=status,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def seed_default_personas(self, organization_id: uuid.UUID) -> Sequence[User]:
        """Seed 5 org-scoped default operational personas without mutating other organizations."""
        default_personas = [
            {
                "name": "Sarah Chen",
                "email": "sarah.chen@ssfa.com",
                "role": UserRole.ADMIN,
                "title": "Chief Compliance Officer",
                "department": "Risk, Trust & Security",
            },
            {
                "name": "Marcus Vance",
                "email": "marcus.vance@ssfa.com",
                "role": UserRole.DATA_OWNER,
                "title": "Principal Data Steward",
                "department": "Enterprise Data Platform",
            },
            {
                "name": "Elena Rostova",
                "email": "elena.rostova@ssfa.com",
                "role": UserRole.REVIEWER,
                "title": "Lead Risk Auditor",
                "department": "Independent Governance & Oversight",
            },
            {
                "name": "Alex Vance",
                "email": "alex.vance@ssfa.com",
                "role": UserRole.DEVELOPER,
                "title": "Autonomous Systems Engineer",
                "department": "AI Operations & Platform Engineering",
            },
            {
                "name": "Devin Zhao",
                "email": "devin.zhao@regulatory-watch.org",
                "role": UserRole.VIEWER,
                "title": "Compliance Observer",
                "department": "Regulatory Assurance & Oversight",
            },
        ]

        for p in default_personas:
            existing_by_email = await self.get_by_email(organization_id, p["email"])
            if not existing_by_email:
                await self.create_user(
                    organization_id=organization_id,
                    name=p["name"],
                    email=p["email"],
                    role=p["role"],
                    title=p["title"],
                    department=p["department"],
                )

        return await self.list_by_organization(organization_id)
