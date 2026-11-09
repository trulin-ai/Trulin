import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT table_name, column_name FROM information_schema.columns WHERE table_name LIKE '%claim%' ORDER BY table_name, ordinal_position"))
        for row in res.fetchall():
            print(f"{row[0]} : {row[1]}")

asyncio.run(main())

