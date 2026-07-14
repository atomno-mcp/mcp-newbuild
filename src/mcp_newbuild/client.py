"""HTTP-клиент к hosted-бэкенду newbuild (api.atomno-mcp.ru/newbuild).

Тонкая обёртка над httpx: один общий AsyncClient, заголовок X-API-Key, маппинг
ошибок в NewbuildError. Никакой бизнес-логики (сбор/нормализация ЕИСЖС, кэш,
скоринг риска, снапшоты сроков — на приватном сервере). Данные корпоративные
(о юрлицах-застройщиках и объектах), ПДн физлиц на нашей стороне не персистятся.
"""

from __future__ import annotations

from typing import Any

import httpx

from . import __version__
from .config import Settings
from .errors import BackendError, BackendUnavailable

_USER_AGENT = f"atomno-mcp-newbuild/{__version__}"


class NewbuildClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
        if settings.token:
            headers["X-API-Key"] = settings.token
        self._client = httpx.AsyncClient(
            base_url=settings.api_base,
            timeout=settings.timeout,
            headers=headers,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = await self._client.post(path, json=payload)
        except httpx.TimeoutException as exc:
            raise BackendUnavailable(f"timeout calling {path}") from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailable(f"network error calling {path}: {exc}") from exc
        return self._parse(resp)

    @staticmethod
    def _parse(resp: httpx.Response) -> dict[str, Any]:
        if resp.status_code >= 400:
            raise BackendError(resp.status_code, _extract_detail(resp))
        try:
            return resp.json()
        except ValueError as exc:
            raise BackendError(resp.status_code, "invalid JSON in response") from exc

    async def developer(self, ident: str) -> dict[str, Any]:
        return await self._post("/developer", {"ident": ident})

    async def declaration(self, object_id: str) -> dict[str, Any]:
        return await self._post("/object/declaration", {"object_id": object_id})

    async def escrow(self, object_id: str) -> dict[str, Any]:
        return await self._post("/object/escrow", {"object_id": object_id})

    async def permit(self, object_id: str) -> dict[str, Any]:
        return await self._post("/object/permit", {"object_id": object_id})

    async def search_objects(
        self,
        region: str | None,
        developer_inn: str | None,
        commissioning_year: int | None,
        stage: str | None,
        escrow: bool | None,
        limit: int,
    ) -> dict[str, Any]:
        return await self._post(
            "/objects/search",
            {
                "region": region,
                "developer_inn": developer_inn,
                "commissioning_year": commissioning_year,
                "stage": stage,
                "escrow": escrow,
                "limit": limit,
            },
        )

    async def developer_risk(self, inn: str) -> dict[str, Any]:
        return await self._post("/developer/risk", {"inn": inn})


def _extract_detail(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:300] or resp.reason_phrase
    if isinstance(body, dict):
        for key in ("message_ru", "detail", "message", "error"):
            if body.get(key):
                return str(body[key])
    return str(body)[:300]
