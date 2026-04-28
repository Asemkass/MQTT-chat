import os
import asyncpg
import asyncio
from app.core.config import logger


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        for i in range(10):
            try:
                self.pool = await asyncpg.create_pool(
                    user=os.getenv("DB_USER", "user"),
                    password=os.getenv("DB_PASSWORD", "password"),
                    database=os.getenv("DB_NAME", "chatdb"),
                    host=os.getenv("DB_HOST", "postgres"),
                    port=5432
                )
                await self.init_tables()
                logger.info("База данных готова!")
                return
            except Exception as e:
                logger.error(f"Ожидание БД... {e}")
                await asyncio.sleep(3)

    async def init_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY, topic VARCHAR(255) NOT NULL,
                    username VARCHAR(50) NOT NULL, text TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_messages_topic ON messages (topic);
                CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages (sent_at DESC);
            """)


db = Database()
