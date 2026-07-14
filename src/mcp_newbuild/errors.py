"""Ошибки клиента — единый тип для MCP-слоя."""

from __future__ import annotations


class NewbuildError(Exception):
    """Базовая ошибка клиента (сетевая / HTTP / валидация ответа)."""


class BackendError(NewbuildError):
    """Бэкенд вернул не-2xx ответ."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"backend {status_code}: {detail}")


class BackendUnavailable(NewbuildError):
    """Бэкенд недоступен (сеть / таймаут)."""
