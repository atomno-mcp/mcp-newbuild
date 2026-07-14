"""Серверный слой: hosted wrappers, tool paths, client singleton."""

from __future__ import annotations

from dataclasses import replace

import pytest

import mcp_newbuild.server as srv
from mcp_newbuild.errors import BackendError, NewbuildError


async def test_no_token_hint(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token=None))
    out = await srv._hosted_call("x", lambda: _fail())
    assert out["error"] == "missing_token"
    assert "MCP_NEWBUILD_API_KEY" in out["message_ru"]
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_disclaimer_injected(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _ok() -> dict:
        return {"results": []}

    out = await srv._hosted_call("x", _ok)
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_hosted_backend_error_500(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _boom() -> dict:
        raise BackendError(500, "down")

    out = await srv._hosted_call("check_developer", _boom)
    assert out["error"] == "backend_error"


async def test_hosted_backend_error_401(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _boom() -> dict:
        raise BackendError(401, "bad")

    out = await srv._hosted_call("check_developer", _boom)
    assert out["error"] == "missing_token"


async def test_hosted_newbuild_error(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _boom() -> dict:
        raise NewbuildError("offline")

    out = await srv._hosted_call("check_developer", _boom)
    assert out["error"] == "unavailable"


@pytest.fixture
def with_token_and_mock_call(monkeypatch):
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k"))

    async def _mock_call(fn):
        return {"ok": True}

    monkeypatch.setattr(srv, "_call", _mock_call)


async def test_check_developer_tool(with_token_and_mock_call) -> None:
    out = await srv.check_developer("7707083893")
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_get_project_declaration_tool(with_token_and_mock_call) -> None:
    out = await srv.get_project_declaration("obj-1")
    assert out["ok"] is True


async def test_check_escrow_tool(with_token_and_mock_call) -> None:
    out = await srv.check_escrow("obj-1")
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_check_construction_permit_tool(with_token_and_mock_call) -> None:
    out = await srv.check_construction_permit("obj-1")
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_list_new_buildings_tool(with_token_and_mock_call) -> None:
    out = await srv.list_new_buildings("Москва", "7707083893", 2026, "монтаж", True, 10)
    assert out["ok"] is True


async def test_get_developer_risk_summary_tool(with_token_and_mock_call) -> None:
    out = await srv.get_developer_risk_summary("7707083893")
    assert out["disclaimer"] == srv.DISCLAIMER


async def test_get_client_singleton(monkeypatch) -> None:
    monkeypatch.setattr(srv, "_client", None)
    monkeypatch.setattr(srv, "_settings", replace(srv._settings, token="k", api_base="http://test"))

    class FakeClient:
        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(srv, "NewbuildClient", lambda _s: FakeClient())
    first = await srv._get_client()
    second = await srv._get_client()
    assert first is second


def test_build_arg_parser_version() -> None:
    parser = srv._build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])


async def _fail() -> dict:
    raise AssertionError("should not be called without token")
