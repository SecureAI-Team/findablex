"""Database seeding script."""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import async_session_maker
from app.models.user import User
from app.models.workspace import Tenant, Workspace, Membership
from app.models.project import Project, QueryItem
from app.models.run import Run


async def seed_database():
    """Seed the database with initial data."""
    async with async_session_maker() as session:
        # Check if already seeded
        result = await session.execute(
            select(User).where(User.email == "admin@findablex.com")
        )
        if result.scalar_one_or_none():
            print("Database already seeded.")
            return
        
        print("Seeding database...")
        
        # ===== Create Super Admin =====
        admin = User(
            email="admin@findablex.com",
            hashed_password=hash_password("admin123456"),
            full_name="系统管理员",
            is_superuser=True,
            email_verified_at=datetime.now(timezone.utc),
        )
        session.add(admin)
        await session.flush()
        print(f"Created admin user: {admin.email}")
        
        # Create admin tenant and workspace
        admin_tenant = Tenant(
            name="管理员工作空间",
            plan="enterprise",
        )
        session.add(admin_tenant)
        await session.flush()
        
        admin_workspace = Workspace(
            tenant_id=admin_tenant.id,
            name="管理员工作空间",
            slug="admin-workspace",
            research_opt_in=False,
        )
        session.add(admin_workspace)
        await session.flush()
        
        admin_membership = Membership(
            user_id=admin.id,
            workspace_id=admin_workspace.id,
            role="admin",
        )
        session.add(admin_membership)
        
        # ===== Create Demo User =====
        demo_user = User(
            email="demo@findablex.com",
            hashed_password=hash_password("demo123456"),
            full_name="演示用户",
            is_superuser=False,
            email_verified_at=datetime.now(timezone.utc),
        )
        session.add(demo_user)
        await session.flush()
        print(f"Created demo user: {demo_user.email}")
        
        # Create demo tenant and workspace
        demo_tenant = Tenant(
            name="演示租户",
            plan="pro",
        )
        session.add(demo_tenant)
        await session.flush()
        
        demo_workspace = Workspace(
            tenant_id=demo_tenant.id,
            name="演示工作区",
            slug="demo-workspace",
            research_opt_in=False,
        )
        session.add(demo_workspace)
        await session.flush()
        print(f"Created workspace: {demo_workspace.name}")
        
        demo_membership = Membership(
            user_id=demo_user.id,
            workspace_id=demo_workspace.id,
            role="admin",
        )
        session.add(demo_membership)
        
        # ===== Create Researcher User =====
        researcher = User(
            email="researcher@findablex.com",
            hashed_password=hash_password("researcher123456"),
            full_name="研究员",
            is_superuser=False,
            email_verified_at=datetime.now(timezone.utc),
        )
        session.add(researcher)
        await session.flush()
        print(f"Created researcher user: {researcher.email}")
        
        # Add researcher to demo workspace with researcher role
        researcher_membership = Membership(
            user_id=researcher.id,
            workspace_id=demo_workspace.id,
            role="researcher",
        )
        session.add(researcher_membership)
        
        # ===== Create Demo Projects =====
        
        # Project 1: Healthcare
        project1 = Project(
            workspace_id=demo_workspace.id,
            name="医疗健康行业 GEO 分析",
            description="针对医疗健康行业的GEO可见性分析项目",
            industry_template="healthcare",
            target_domains=["example-hospital.com", "health-clinic.cn"],
            status="active",
            created_by=demo_user.id,
        )
        session.add(project1)
        await session.flush()
        print(f"Created project: {project1.name}")
        
        # Add queries for project 1 with full metadata
        healthcare_queries = [
            {"text": "北京最好的骨科医院", "stage": "decision", "type": "recommendation", "risk": "high", "role": "sales"},
            {"text": "腰椎间盘突出怎么治疗", "stage": "awareness", "type": "definition", "risk": "low", "role": "technical"},
            {"text": "三甲医院和二甲医院有什么区别", "stage": "consideration", "type": "comparison", "risk": "medium", "role": "marketing"},
            {"text": "医保报销流程是什么", "stage": "consideration", "type": "howto", "risk": "medium", "role": "compliance"},
            {"text": "体检项目有哪些", "stage": "awareness", "type": "definition", "risk": "low", "role": "marketing"},
        ]
        
        for i, q in enumerate(healthcare_queries):
            query = QueryItem(
                project_id=project1.id,
                query_text=q["text"],
                query_type=q["type"],
                stage=q["stage"],
                risk_level=q["risk"],
                target_role=q["role"],
                position=i,
            )
            session.add(query)
        
        # Create a completed run for project 1
        run1 = Run(
            project_id=project1.id,
            run_number=1,
            run_type="checkup",
            status="completed",
            input_method="import",
            health_score=72,
            parameters={"input_format": "paste"},
            created_by=demo_user.id,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(run1)
        
        # Project 2: Finance
        project2 = Project(
            workspace_id=demo_workspace.id,
            name="金融科技品牌监测",
            description="监测金融科技品牌在AI引擎中的可见性",
            industry_template="finance",
            target_domains=["fintech-demo.com"],
            status="active",
            created_by=demo_user.id,
        )
        session.add(project2)
        await session.flush()
        print(f"Created project: {project2.name}")
        
        finance_queries = [
            {"text": "最好的理财APP推荐", "stage": "decision", "type": "recommendation", "risk": "critical", "role": "sales"},
            {"text": "银行理财和基金哪个好", "stage": "consideration", "type": "comparison", "risk": "high", "role": "marketing"},
            {"text": "如何选择信用卡", "stage": "awareness", "type": "howto", "risk": "medium", "role": "marketing"},
        ]
        
        for i, q in enumerate(finance_queries):
            query = QueryItem(
                project_id=project2.id,
                query_text=q["text"],
                query_type=q["type"],
                stage=q["stage"],
                risk_level=q["risk"],
                target_role=q["role"],
                position=i,
            )
            session.add(query)
        
        # Create a completed run for project 2
        run2 = Run(
            project_id=project2.id,
            run_number=1,
            run_type="checkup",
            status="completed",
            input_method="import",
            health_score=85,
            parameters={"input_format": "csv"},
            created_by=demo_user.id,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(run2)
        
        await session.commit()
        
        print("\n" + "=" * 50)
        print("Database seeding completed!")
        print("=" * 50)
        print("\nDefault accounts:")
        print("  Admin:      admin@findablex.com / admin123456 (平台管理员)")
        print("  Researcher: researcher@findablex.com / researcher123456 (研究员)")
        print("  Demo:       demo@findablex.com / demo123456 (演示用户)")
        print("\nDemo workspace: demo-workspace")
        print("Demo projects:")
        print("  - 医疗健康行业 GEO 分析 (Health Score: 72)")
        print("  - 金融科技品牌监测 (Health Score: 85)")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed_database())
