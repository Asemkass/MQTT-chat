from app.db.database import db


class MessageRepository:
    async def save_message(self, topic, username, text, sent_at):
        async with db.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO messages (topic, username, text, sent_at) VALUES ($1, $2, $3, $4)",
                topic, username, text, sent_at
            )

    async def get_history(self, topic, limit=50):
        async with db.pool.acquire() as conn:
            return await conn.fetch(
                "SELECT username, text, sent_at FROM messages WHERE topic=$1 ORDER BY sent_at DESC LIMIT $2",
                topic, limit
            )
