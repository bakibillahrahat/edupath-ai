from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

import app.modules.auth.service as auth_module
from app.core.exceptions import AuthDisabledError, AuthenticationError
from app.core.security import create_access_token
from app.modules.auth.models import User
from app.modules.auth.service import AuthService


class FakeRedis:
    """Minimal in-memory stand-in for the subset of redis.asyncio.Redis this
    module uses -- avoids any real network dependency in unit tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def set(self, key, value, ex=None):
        self._store[key] = value

    async def get(self, key):
        return self._store.get(key)

    async def delete(self, key):
        self._store.pop(key, None)

    async def exists(self, key):
        return 1 if key in self._store else 0


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, User] = {}
        self._by_email: dict[str, User] = {}
        self._by_sub: dict[str, User] = {}

    async def get(self, session, user_id):
        return self._by_id.get(user_id)

    async def get_by_google_sub(self, session, google_sub):
        return self._by_sub.get(google_sub)

    async def get_by_email(self, session, email):
        return self._by_email.get(email)

    async def create(self, session, user):
        user.id = uuid4()
        self._index(user)
        return user

    async def update(self, session, user):
        self._index(user)
        return user

    def _index(self, user: User) -> None:
        self._by_id[user.id] = user
        self._by_email[user.email] = user
        if user.google_sub:
            self._by_sub[user.google_sub] = user


@pytest.fixture(autouse=True)
def _fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(auth_module, "get_redis_client", lambda: fake)
    return fake


@pytest.mark.asyncio
async def test_dev_login_creates_a_user_when_google_not_configured(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "google_client_id", None)
    monkeypatch.setattr(auth_module.settings, "google_client_secret", None)
    service = AuthService(repository=FakeUserRepository())

    user, token = await service.dev_login(SimpleNamespace(), email="student@example.com", name="Test Student")

    assert user.email == "student@example.com"
    assert user.google_sub is None
    assert token

    # Logging in again with the same email returns the SAME user, not a duplicate.
    user2, _ = await service.dev_login(SimpleNamespace(), email="student@example.com", name="Test Student")
    assert user2.id == user.id


@pytest.mark.asyncio
async def test_dev_login_disabled_when_google_is_configured(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "google_client_id", "real-client-id")
    monkeypatch.setattr(auth_module.settings, "google_client_secret", "real-secret")
    service = AuthService(repository=FakeUserRepository())

    with pytest.raises(AuthDisabledError):
        await service.dev_login(SimpleNamespace(), email="student@example.com", name=None)


@pytest.mark.asyncio
async def test_get_current_user_returns_user_for_valid_token():
    repository = FakeUserRepository()
    service = AuthService(repository=repository)
    user = User(email="student@example.com", name="Test", google_sub=None)
    user = await repository.create(SimpleNamespace(), user)
    token = create_access_token(str(user.id))

    result = await service.get_current_user(SimpleNamespace(), token)

    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_current_user_rejects_garbage_token():
    service = AuthService(repository=FakeUserRepository())

    with pytest.raises(AuthenticationError):
        await service.get_current_user(SimpleNamespace(), "not-a-real-token")


@pytest.mark.asyncio
async def test_get_current_user_rejects_token_for_deleted_user():
    service = AuthService(repository=FakeUserRepository())
    token = create_access_token(str(uuid4()))  # no such user was ever created

    with pytest.raises(AuthenticationError):
        await service.get_current_user(SimpleNamespace(), token)


@pytest.mark.asyncio
async def test_logout_blacklists_token_and_get_current_user_then_rejects_it(_fake_redis):
    repository = FakeUserRepository()
    service = AuthService(repository=repository)
    user = await repository.create(SimpleNamespace(), User(email="student@example.com", name="Test", google_sub=None))
    token = create_access_token(str(user.id))

    # Works before logout.
    assert (await service.get_current_user(SimpleNamespace(), token)).id == user.id

    await service.logout(token)

    with pytest.raises(AuthenticationError):
        await service.get_current_user(SimpleNamespace(), token)


@pytest.mark.asyncio
async def test_get_config_reports_dev_mock_when_google_unconfigured(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "google_client_id", None)
    monkeypatch.setattr(auth_module.settings, "google_client_secret", None)
    service = AuthService(repository=FakeUserRepository())

    config = service.get_config()

    assert config.mode == "dev-mock"


@pytest.mark.asyncio
async def test_get_config_reports_google_when_configured(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "google_client_id", "id")
    monkeypatch.setattr(auth_module.settings, "google_client_secret", "secret")
    service = AuthService(repository=FakeUserRepository())

    config = service.get_config()

    assert config.mode == "google"
    assert config.google_login_url == "/api/v1/auth/login"
