from fastapi import WebSocket
from app.core.config import logger


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str):
        await websocket.accept()
        self.active_connections.setdefault(topic, []).append(websocket)

    def disconnect(self, websocket: WebSocket, topic: str):
        if topic in self.active_connections:
            self.active_connections[topic].remove(websocket)

    async def broadcast(self, topic: str, message: dict):
        for connection in self.active_connections.get(topic, []):
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()
