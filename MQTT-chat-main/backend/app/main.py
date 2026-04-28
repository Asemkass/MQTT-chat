import json
import asyncio
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.db.database import db
from app.core.security import decode_token, hash_password, verify_password, create_access_token
from app.core.config import logger, MAX_MSG_LENGTH, WS_HEARTBEAT_TIMEOUT
from app.api.websocket import manager
from app.services.mqtt_service import MQTTService
from app.repositories.message_repo import MessageRepository

# --- Схемы данных ---


class UserAuth(BaseModel):
    username: str
    password: str

# --- Жизненный цикл приложения (Lifespan) ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Действия при старте
    await db.connect()
    mqtt_task = asyncio.create_task(mqtt_service.run())
    logger.info("Приложение запущено и MQTT клиент запущен.")

    yield

    # Действия при выключении (Graceful Shutdown)
    logger.info("Завершение работы...")
    mqtt_service.stop_event.set()
    mqtt_task.cancel()
    if db.pool:
        await db.pool.close()
    logger.info("Все соединения закрыты.")

app = FastAPI(lifespan=lifespan)

# Настройка CORS (чтобы браузер разрешал запросы)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mqtt_service = MQTTService(manager.broadcast)
message_repo = MessageRepository()

# --- API Роуты ---


@app.post("/api/register")
async def register(user: UserAuth):
    async with db.pool.acquire() as conn:
        try:
            hpw = hash_password(user.password)
            await conn.execute(
                "INSERT INTO users (username, password) VALUES ($1, $2)",
                user.username, hpw
            )
            return {"status": "created"}
        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
            raise HTTPException(status_code=409, detail="User already exists")


@app.post("/api/login")
async def login(user: UserAuth):
    async with db.pool.acquire() as conn:
        res = await conn.fetchrow("SELECT password FROM users WHERE username=$1", user.username)
        if not res or not verify_password(user.password, res[0]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"sub": user.username})
        return {"token": token}


@app.get("/api/messages")
async def get_messages(topic: str, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        token = authorization.split(" ")[1]
        decode_token(token)
        rows = await message_repo.get_history(topic)
        return [
            {"username": r[0], "text": r[1], "sent_at": r[2].isoformat() + "Z"}
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

# --- WebSocket ---


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, topic: str = Query(...), token: str = Query(...)):
    try:
        username = decode_token(token)["sub"]
    except Exception:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, topic)
    try:
        while True:
            # 3. Heartbeat (Тайм-аут ожидания)
            data = await asyncio.wait_for(websocket.receive_text(), timeout=WS_HEARTBEAT_TIMEOUT)
            msg_json = json.loads(data)

            # 4. Ограничение размера сообщения
            text = msg_json.get("text", "")[:MAX_MSG_LENGTH]

            payload = {
                "username": username,
                "text": text,
                "sent_at": datetime.now(timezone.utc).isoformat()
            }

            if mqtt_service.client:
                await mqtt_service.client.publish(topic, payload=json.dumps(payload))

    except (WebSocketDisconnect, asyncio.TimeoutError):
        manager.disconnect(websocket, topic)
    except Exception as e:
        logger.error(f"WS Error: {e}")
        manager.disconnect(websocket, topic)

# --- Раздача статики (Фронтенд) ---
# Проверяем путь для Docker (/app/frontend) и локальный путь (../frontend)
current_dir = os.path.dirname(__file__)
local_frontend = os.path.abspath(os.path.join(current_dir, "../../frontend"))
docker_frontend = "/app/frontend"

frontend_path = docker_frontend if os.path.exists(
    docker_frontend) else local_frontend

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
    logger.info(f"Статика подключена из: {frontend_path}")
else:
    logger.warning(f"Папка фронтенда не найдена: {frontend_path}")
