"""
Seed script — creates default admin user and sample data.
Run: python scripts/seed.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from core.database import create_tables, AsyncSessionLocal
from core.auth import hash_password
from models.user import User, UserRole
from sqlalchemy import select


async def seed():
    print("Creating tables...")
    await create_tables()

    async with AsyncSessionLocal() as db:
        # Check if admin exists
        q = await db.execute(select(User).where(User.username == 'admin'))
        existing = q.scalar_one_or_none()
        if existing:
            print("Admin user already exists, skipping.")
            return

        admin = User(
            username='admin',
            email='admin@inspectai.local',
            hashed_password=hash_password('admin123'),
            full_name='Администратор системы',
            role=UserRole.ADMIN,
        )
        inspector = User(
            username='inspector',
            email='inspector@inspectai.local',
            hashed_password=hash_password('inspector123'),
            full_name='Инспектор Иванов И.И.',
            role=UserRole.INSPECTOR,
        )
        analyst = User(
            username='analyst',
            email='analyst@inspectai.local',
            hashed_password=hash_password('analyst123'),
            full_name='Аналитик Петрова А.В.',
            role=UserRole.ANALYST,
        )
        db.add_all([admin, inspector, analyst])
        await db.commit()
        print("Created users:")
        print("  admin / admin123 (Администратор)")
        print("  inspector / inspector123 (Инспектор)")
        print("  analyst / analyst123 (Аналитик)")
        print("\nSeed completed successfully!")


if __name__ == '__main__':
    asyncio.run(seed())
