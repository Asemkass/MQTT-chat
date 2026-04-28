import json
import asyncio
import os
from aiomqtt import Client
from app.core.config import logger
from app.repositories.message_repo import MessageRepository
from datetime import datetime


class MQTTService:
    def __init__(self, broadcast_func):
        self.client = None
        self.stop_event = asyncio.Event()
        self.broadcast_func = broadcast_func
        self.repo = MessageRepository()

    async def run(self):
        mqtt_host = os.getenv("MQTT_HOST", "mosquitto")
        while not self.stop_event.is_set():
            try:
                async with Client(hostname=mqtt_host, port=1883) as client:
                    self.client = client
                    await client.subscribe("#")
                    logger.info("Успешное подключение к MQTT!")
                    async for message in client.messages:
                        if self.stop_event.is_set():
                            break
                        await self._handle_message(message)
            except Exception as e:
                if self.stop_event.is_set():
                    break
                logger.warning(f"Ошибка MQTT: {e}. Переподключение...")
                await asyncio.sleep(5)

    async def _handle_message(self, message):
        try:
            payload = json.loads(message.payload.decode())
            topic = str(message.topic)
            dt = datetime.fromisoformat(payload["sent_at"].replace(
                "Z", "+00:00")).replace(tzinfo=None)
            await self.repo.save_message(topic, payload["username"], payload["text"], dt)
            await self.broadcast_func(topic, payload)
        except Exception as e:
            logger.error(f"Ошибка обработки MQTT: {e}")
