"""Конфигурация тонкого клиента из переменных окружения.

Все тулы (застройщик/декларация/эскроу/разрешение/поиск/риск) идут через
hosted-бэкенд и требуют ключ Pro.

    MCP_NEWBUILD_API_BASE — базовый URL hosted-бэкенда (default: публичный прод).
    MCP_NEWBUILD_API_KEY  — API-ключ (заголовок X-API-Key). Без него тулы → подсказка.
    MCP_NEWBUILD_TIMEOUT  — таймаут HTTP в секундах (default 30).
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

    @classmethod
    def from_env(cls) -> Settings:
        base = (os.environ.get("MCP_NEWBUILD_API_BASE") or DEFAULT_API_BASE).rstrip("/")
        token = os.environ.get("MCP_NEWBUILD_API_KEY") or None
        try:
            timeout = float(os.environ.get("MCP_NEWBUILD_TIMEOUT") or DEFAULT_TIMEOUT)
        except ValueError:
            timeout = DEFAULT_TIMEOUT
        return cls(api_base=base, token=token, timeout=timeout)

    @property
    def has_token(self) -> bool:
        return bool(self.token)
