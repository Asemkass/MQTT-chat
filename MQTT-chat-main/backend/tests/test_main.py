import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_auth_flow():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Регистрация
        reg = await ac.post("/api/register", json={"username": "testit", "password": "123"})
        assert reg.status_code in [200, 409]

        # 2. Логин
        log = await ac.post("/api/login", json={"username": "testit", "password": "123"})
        assert log.status_code == 200
        token = log.json()["token"]

        # 3. История (с токеном)
        hist = await ac.get("/api/messages?topic=test", headers={"Authorization": f"Bearer {token}"})
        assert hist.status_code == 200


def test_config():
    from app.core.config import MAX_MSG_LENGTH
    assert MAX_MSG_LENGTH == 2000
