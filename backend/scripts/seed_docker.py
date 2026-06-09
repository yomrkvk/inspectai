"""
Docker seed — called automatically on container startup after alembic upgrade.
Creates default users if they don't exist.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import sys
from pathlib import Path

# Добавляем корневую папку backend в путь Python
sys.path.append(str(Path(__file__).parent.parent))

from core.database import AsyncSessionLocal
from core.auth import hash_password
from models.user import User, UserRole
from sqlalchemy import select


async def seed():
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(User).where(User.username == 'admin'))
        if q.scalar_one_or_none():
            print("[seed] Users already exist, skipping.")
            return

        users = [
            User(username='admin', email='admin@inspectai.local',
                 hashed_password=hash_password('admin123'),
                 full_name='Администратор системы', role=UserRole.ADMIN),
            User(username='inspector', email='inspector@inspectai.local',
                 hashed_password=hash_password('inspector123'),
                 full_name='Инспектор Иванов И.И.', role=UserRole.INSPECTOR),
            User(username='analyst', email='analyst@inspectai.local',
                 hashed_password=hash_password('analyst123'),
                 full_name='Аналитик Петрова А.В.', role=UserRole.ANALYST),
        ]
        db.add_all(users)
        await db.commit()
        print("[seed] Created: admin / inspector / analyst")


if __name__ == '__main__':
    asyncio.run(seed())
