import os
import json
import asyncio
import asyncpg
import jwt
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager  # ЭТОТ ИМПОРТ БЫЛ ПРОПУЩЕН

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from aiomqtt import Client, MqttError
from fastapi.staticfiles import StaticFiles

# --- НАСТРОЙКИ ---
JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_key")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db_pool = None
mqtt_client_global = None

# --- МЕНЕДЖЕР WEBSOCKET СОЕДИНЕНИЙ ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str):
        await websocket.accept()
        if topic not in self.active_connections:
            self.active_connections[topic] = []
        self.active_connections[topic].append(websocket)

    def disconnect(self, websocket: WebSocket, topic: str):
        if topic in self.active_connections:
            self.active_connections[topic] = [w for w in self.active_connections[topic] if w != websocket]

    async def broadcast(self, topic: str, message: dict):
        if topic in self.active_connections:
            for connection in self.active_connections[topic]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# --- ФОНОВАЯ ЗАДАЧА MQTT ---
async def listen_mqtt():
    mqtt_host = os.getenv("MQTT_HOST", "mosquitto")
    while True:
        try:
            async with Client(hostname=mqtt_host, port=1883) as client:
                global mqtt_client_global
                mqtt_client_global = client
                await client.subscribe("#")
                print("Успешное подключение к MQTT!")
                
                async for message in client.messages:
                    try:
                        payload = json.loads(message.payload.decode())
                        topic = str(message.topic)
                        
                        # Сохранение в БД
                        async with db_pool.acquire() as conn:
                            # Парсим дату и убираем таймзону для Postgres
                            dt = datetime.fromisoformat(payload["sent_at"].replace("Z", "+00:00"))
                            await conn.execute(
                                "INSERT INTO messages (topic, username, text, sent_at) VALUES ($1, $2, $3, $4)",
                                topic, payload["username"], payload["text"], dt.replace(tzinfo=None)
                            )
                        
                        # Рассылка по WebSocket
                        await manager.broadcast(topic, payload)
                    except Exception as e:
                        print(f"Ошибка обработки сообщения: {e}")
        except Exception as e:
            print(f"Ошибка MQTT: {e}. Переподключение через 5 сек...")
            await asyncio.sleep(5)

# --- ЖИЗНЕННЫЙ ЦИКЛ ПРИЛОЖЕНИЯ ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    # Параметры подключения к БД
    db_user = os.getenv("DB_USER", "user")
    db_pass = os.getenv("DB_PASSWORD", "password")
    db_name = os.getenv("DB_NAME", "chatdb")
    db_host = os.getenv("DB_HOST", "postgres")

    # Ждем базу данных
    for i in range(10):
        try:
            db_pool = await asyncpg.create_pool(
                user=db_user, password=db_pass,
                database=db_name, host=db_host, port=5432
            )
            # Автоматическое создание таблиц
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        topic VARCHAR(255) NOT NULL,
                        username VARCHAR(50) NOT NULL,
                        text TEXT NOT NULL,
                        sent_at TIMESTAMP DEFAULT NOW()
                    );
                """)
            print("База данных готова!")
            break
        except Exception as e:
            print(f"Ожидание БД... ({e})")
            await asyncio.sleep(3)
    
    # Запуск фонового клиента MQTT
    mqtt_task = asyncio.create_task(listen_mqtt())
    yield
    # Завершение
    mqtt_task.cancel()
    if db_pool:
        await db_pool.close()

app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- МОДЕЛИ И API ---
class UserAuth(BaseModel):
    username: str
    password: str

@app.post("/api/register")
async def register(user: UserAuth):
    async with db_pool.acquire() as conn:
        try:
            hashed_pw = pwd_context.hash(user.password)
            await conn.execute("INSERT INTO users (username, password) VALUES ($1, $2)", 
                               user.username, hashed_pw)
            return {"status": "created"}
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=409, detail="User already exists")

@app.post("/api/login")
async def login(user: UserAuth):
    async with db_pool.acquire() as conn:
        res = await conn.fetchrow("SELECT password FROM users WHERE username=$1", user.username)
        if not res or not pwd_context.verify(user.password, res[0]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = jwt.encode({
            "sub": user.username, 
            "exp": datetime.now(timezone.utc) + timedelta(days=1)
        }, JWT_SECRET, algorithm=ALGORITHM)
        return {"token": token}

@app.get("/api/messages")
async def get_messages(topic: str, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401)
    try:
        token = authorization.split(" ")[1]
        jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except:
        raise HTTPException(status_code=401)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT username, text, sent_at FROM messages WHERE topic=$1 ORDER BY sent_at DESC LIMIT 50", 
            topic
        )
        # Возвращаем историю (разворачиваем, чтобы старые были сверху)
        return [{"username": r[0], "text": r[1], "sent_at": r[2].isoformat()+"Z"} for r in rows]

# --- WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, topic: str = Query(...), token: str = Query(...)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        username = payload["sub"]
    except:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, topic)
    try:
        while True:
            data = await websocket.receive_text()
            json_data = json.loads(data)
            
            message_to_mqtt = {
                "username": username,
                "text": json_data["text"],
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
            
            if mqtt_client_global:
                await mqtt_client_global.publish(topic, payload=json.dumps(message_to_mqtt))
    except WebSocketDisconnect:
        manager.disconnect(websocket, topic)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(websocket, topic)

# --- РАЗДАЧА ФРОНТЕНДА ---
# Путь внутри контейнера /app/frontend
app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="static")