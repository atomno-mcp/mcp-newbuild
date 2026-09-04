"""Конфигурация из переменных окружения.

Ключ договора ЕИСЖС — client_id и client_secret клиента
(оферта API ЕИСЖС, бизнес.дом.рф). Спецификация методов закрыта договором:
при заданных учётках запрос с выдуманными путями не отправляем.

Наше размещение — отдельная услуга (MCP_NEWBUILD_API_KEY).
Своего договора с ЕИСЖС у нас нет.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_API_BASE = "https://api.atomno-mcp.ru/newbuild"
DEFAULT_TIMEOUT = 30.0


@dataclass(frozen=True)
class Settings:
    api_base: str
    token: str | None
    timeout: float
    eiszhs_client_id: str | None = None
    eiszhs_client_secret: str | None = None
    eiszhs_base_url: str | None = None
    eiszhs_token_url: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        base = (os.environ.get("MCP_NEWBUILD_API_BASE") or DEFAULT_API_BASE).rstrip("/")
        token = os.environ.get("MCP_NEWBUILD_API_KEY") or None
        try:
            timeout = float(os.environ.get("MCP_NEWBUILD_TIMEOUT") or DEFAULT_TIMEOUT)
        except ValueError:
            timeout = DEFAULT_TIMEOUT
        client_id = (os.environ.get("MCP_NEWBUILD_EISZHS_CLIENT_ID") or "").strip() or None
        secret = os.environ.get("MCP_NEWBUILD_EISZHS_CLIENT_SECRET") or None
        if secret is not None and not secret.strip():
            secret = None
        eiszhs_base = (os.environ.get("MCP_NEWBUILD_EISZHS_BASE_URL") or "").strip() or None
        token_url = (os.environ.get("MCP_NEWBUILD_EISZHS_TOKEN_URL") or "").strip() or None
        return cls(
            api_base=base,
            token=token,
            timeout=timeout,
            eiszhs_client_id=client_id,
            eiszhs_client_secret=secret,
            eiszhs_base_url=eiszhs_base,
            eiszhs_token_url=token_url,
        )

    @property
    def has_token(self) -> bool:
        return bool(self.token)

    @property
    def has_eiszhs(self) -> bool:
        return bool(self.eiszhs_client_id and self.eiszhs_client_secret)
