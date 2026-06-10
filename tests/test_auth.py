import pytest
from services.auth import get_access_message, get_user


@pytest.mark.asyncio
async def test_get_user_found(monkeypatch, sample_employees):
    async def fake_refresh():
        return sample_employees

    monkeypatch.setattr("services.auth.refresh_employees", fake_refresh)
    user = await get_user(123)
    assert user is not None
    assert user["full_name"] == "Аня Фролова"
    assert user["role"] == "curator"


@pytest.mark.asyncio
async def test_get_user_not_found(monkeypatch):
    async def fake_refresh():
        return []

    monkeypatch.setattr("services.auth.refresh_employees", fake_refresh)
    assert await get_user(999) is None


@pytest.mark.asyncio
async def test_get_user_inactive(monkeypatch):
    async def fake_employees():
        return [
            {
                "telegram_id": 123,
                "full_name": "Аня",
                "role": "curator",
                "is_active": False,
            }
        ]

    monkeypatch.setattr("services.auth.refresh_employees", fake_employees)
    assert await get_user(123) is None


@pytest.mark.asyncio
async def test_get_user_string_telegram_id_not_matched(monkeypatch):
    async def fake_employees():
        return [
            {
                "telegram_id": "123",
                "full_name": "Аня",
                "role": "curator",
                "is_active": True,
            }
        ]

    monkeypatch.setattr("services.auth.refresh_employees", fake_employees)
    assert await get_user(123) is None


@pytest.mark.asyncio
async def test_get_access_message_when_employees_empty(monkeypatch):
    async def fake_employees():
        return []

    monkeypatch.setattr("services.auth.refresh_employees", fake_employees)
    message = await get_access_message(555)
    assert "не смог загрузить список сотрудников" in message
    assert "GAS_WEBAPP_URL" in message


@pytest.mark.asyncio
async def test_get_access_message_when_user_missing(monkeypatch, sample_employees):
    async def fake_employees():
        return sample_employees

    monkeypatch.setattr("services.auth.refresh_employees", fake_employees)
    message = await get_access_message(999)
    assert "555" not in message
    assert "999" in message
    assert "Сотрудники" in message
