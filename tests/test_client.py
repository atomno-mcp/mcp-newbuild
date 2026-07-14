"""HTTP-клиент к hosted-бэкенду: happy path, 4xx/5xx, таймаут (respx-моки)."""

from __future__ import annotations

import httpx
import pytest
import respx

from mcp_newbuild.client import NewbuildClient
from mcp_newbuild.config import Settings
from mcp_newbuild.errors import BackendError, BackendUnavailable

BASE = "http://test/newbuild"


def _client() -> NewbuildClient:
    return NewbuildClient(Settings(api_base=BASE, token="k", timeout=5.0))


@respx.mock
async def test_developer_happy_path() -> None:
    respx.post(f"{BASE}/developer").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "ООО СтройГрупп",
                "in_registry": True,
                "objects_total": 5,
                "source": "ЕИСЖС/наш.дом.рф",
            },
        )
    )
    c = _client()
    try:
        out = await c.developer("7701234567")
        assert out["name"] == "ООО СтройГрупп"
        assert out["source"] == "ЕИСЖС/наш.дом.рф"
    finally:
        await c.aclose()


@respx.mock
async def test_search_sends_filters() -> None:
    route = respx.post(f"{BASE}/objects/search").mock(
        return_value=httpx.Response(200, json={"results": [], "total": 0})
    )
    c = _client()
    try:
        out = await c.search_objects("Москва", "7701234567", 2026, "монтаж", True, 20)
        assert out["total"] == 0
        body = route.calls.last.request.read()
        assert b"7701234567" in body
        assert b"\\u041c" in body or "Москва".encode() in body
    finally:
        await c.aclose()


@respx.mock
async def test_backend_401() -> None:
    respx.post(f"{BASE}/object/escrow").mock(
        return_value=httpx.Response(401, json={"error": "unauthorized"})
    )
    c = _client()
    try:
        with pytest.raises(BackendError) as ei:
            await c.escrow("OBJ-12345")
        assert ei.value.status_code == 401
    finally:
        await c.aclose()


@respx.mock
async def test_backend_500() -> None:
    respx.post(f"{BASE}/developer/risk").mock(return_value=httpx.Response(500, text="boom"))
    c = _client()
    try:
        with pytest.raises(BackendError) as ei:
            await c.developer_risk("7701234567")
        assert ei.value.status_code == 500
    finally:
        await c.aclose()


@respx.mock
async def test_timeout() -> None:
    respx.post(f"{BASE}/object/permit").mock(side_effect=httpx.TimeoutException("slow"))
    c = _client()
    try:
        with pytest.raises(BackendUnavailable):
            await c.permit("OBJ-12345")
    finally:
        await c.aclose()
