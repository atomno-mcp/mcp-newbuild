"""FastMCP entrypoint для atomno-mcp-newbuild.

Работа на ключе клиента ЕИСЖС: client_id + client_secret из договора-оферты.
Спецификация методов закрыта — выдуманный обмен не отправляем.
Без ключа — честный отказ, не пустая карточка. Справочно, не инвестрекомендация.
"""

from __future__ import annotations

import argparse
import asyncio
import atexit
import logging
import os
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from . import __version__
from .client import NewbuildClient
from .config import Settings
from .errors import BackendError, NewbuildError

logger = logging.getLogger("mcp_newbuild")

_SUPPORTED_TRANSPORTS = ("stdio", "http", "sse", "streamable-http")
_DEFAULT_TRANSPORT = "stdio"
_DEFAULT_HTTP_HOST = "127.0.0.1"
_DEFAULT_HTTP_PORT = 8000
_VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

DISCLAIMER = (
    "Данные справочные, из официального ЕИСЖС/наш.дом.рф; не является "
    "инвестиционной рекомендацией; проверяйте первоисточник перед сделкой. "
    "Не аффилировано с ДОМ.РФ/ЕИСЖС."
)

mcp: FastMCP = FastMCP(
    name="atomno-mcp-newbuild",
    instructions=(
        "Russian new-build MCP. Official EISZHS API uses the client's "
        "client_id and client_secret. Method specification is behind the "
        "contract — we do not invent endpoints. Without credentials the tools "
        "refuse honestly, not with an empty card. We have no EISZHS contract "
        "of our own; live client keys have not been verified. Advisory only."
    ),
)

_client: NewbuildClient | None = None
_client_lock = asyncio.Lock()
_settings = Settings.from_env()


async def _get_client() -> NewbuildClient:
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is None:
            _client = NewbuildClient(_settings)
            atexit.register(_close_client_atexit)
    assert _client is not None
    return _client


def _close_client_atexit() -> None:
    if _client is None:
        return
    try:
        asyncio.run(_client.aclose())
    except RuntimeError:
        pass


SOURCE_EISZHS = "API ЕИСЖС (бизнес.дом.рф), договор клиента"

_NOT_CONFIGURED = (
    "Доступ к ЕИСЖС не настроен. Нужны MCP_NEWBUILD_EISZHS_CLIENT_ID и "
    "MCP_NEWBUILD_EISZHS_CLIENT_SECRET из вашего договора-оферты "
    "(страница https://бизнес.дом.рф/api-еисжс). Своего договора с ЕИСЖС "
    "у нас нет; на живом ключе клиента обмен не проверяли. "
    "Наше размещение — отдельная услуга: MCP_NEWBUILD_API_KEY. "
    "Это не ответ «застройщик / объект не найден»."
)

_SPEC_CLOSED = (
    "Учётка ЕИСЖС задана, но перечень методов и форматы закрыты договором "
    "(спецификация на странице ПО после заключения оферты). "
    "Запрос с выдуманными путями не отправляем. Когда будет описание — "
    "подключим методы. На живом ключе не проверяли. "
    "Это не ответ «не найдено»."
)


def _with_disclaimer(payload: dict[str, Any]) -> dict[str, Any]:
    payload.setdefault("disclaimer", DISCLAIMER)
    return payload


def _not_configured() -> dict[str, Any]:
    return _with_disclaimer(
        {
            "ready": False,
            "error": "source_not_configured",
            "message_ru": _NOT_CONFIGURED,
            "source": SOURCE_EISZHS,
        }
    )


def _spec_closed() -> dict[str, Any]:
    return _with_disclaimer(
        {
            "ready": False,
            "error": "spec_closed",
            "message_ru": _SPEC_CLOSED,
            "source": SOURCE_EISZHS,
        }
    )


async def _hosted_call(name: str, coro_factory) -> dict[str, Any]:
    if not _settings.has_token:
        return _not_configured()
    try:
        result = await coro_factory()
        return _with_disclaimer(result)
    except BackendError as exc:
        if exc.status_code in (401, 403):
            return _with_disclaimer(
                {
                    "ready": False,
                    "error": "invalid_credentials",
                    "message_ru": (
                        "Ключ нашего размещения (MCP_NEWBUILD_API_KEY) не принят. "
                        "Это не ответ «объект не найден»."
                    ),
                    "source": "наше размещение atomno-mcp",
                }
            )
        logger.warning("%s backend %s: %s", name, exc.status_code, exc.detail)
        return _with_disclaimer(
            {"error": "backend_error", "status": exc.status_code, "message": exc.detail}
        )
    except NewbuildError as exc:
        logger.warning("%s failed: %s", name, exc)
        return _with_disclaimer({"error": "unavailable", "message": str(exc)})


async def _source_or_hosted(name: str, coro_factory) -> dict[str, Any]:
    if _settings.has_eiszhs:
        return _spec_closed()
    if _settings.has_token:
        return await _hosted_call(name, coro_factory)
    return _not_configured()


async def _call(fn) -> dict[str, Any]:
    client = await _get_client()
    return await fn(client)


@mcp.tool
async def check_developer(
    ident: Annotated[str, Field(min_length=1, description="ИНН или ОГРН застройщика (юрлица).")],
) -> dict[str, Any]:
    """Карточка застройщика: ключ ЕИСЖС клиента или честный отказ. Описание методов закрыто — запрос не выдумываем."""
    return await _source_or_hosted(
        "check_developer",
        lambda: _call(lambda c: c.developer(ident)),
    )


@mcp.tool
async def get_project_declaration(
    object_id: Annotated[str, Field(min_length=1, description="Идентификатор объекта (строящегося дома/ЖК) в ЕИСЖС.")],
) -> dict[str, Any]:
    """Проектная декларация: ключ ЕИСЖС клиента или честный отказ. Описание методов закрыто."""
    return await _source_or_hosted(
        "get_project_declaration",
        lambda: _call(lambda c: c.declaration(object_id)),
    )


@mcp.tool
async def check_escrow(
    object_id: Annotated[str, Field(min_length=1, description="Идентификатор объекта в ЕИСЖС.")],
) -> dict[str, Any]:
    """Эскроу: ключ ЕИСЖС клиента или честный отказ. Описание методов закрыто."""
    return await _source_or_hosted(
        "check_escrow",
        lambda: _call(lambda c: c.escrow(object_id)),
    )


@mcp.tool
async def check_construction_permit(
    object_id: Annotated[str, Field(min_length=1, description="Идентификатор объекта в ЕИСЖС.")],
) -> dict[str, Any]:
    """Разрешение на строительство: ключ ЕИСЖС клиента или честный отказ. Описание методов закрыто."""
    return await _source_or_hosted(
        "check_construction_permit",
        lambda: _call(lambda c: c.permit(object_id)),
    )


@mcp.tool
async def list_new_buildings(
    region: Annotated[str | None, Field(default=None, description="Регион/субъект РФ для фильтрации.")] = None,
    developer_inn: Annotated[str | None, Field(default=None, description="ИНН застройщика — все объекты его портфеля.")] = None,
    commissioning_year: Annotated[int | None, Field(default=None, ge=2000, le=2100, description="Год планируемого ввода в эксплуатацию.")] = None,
    stage: Annotated[str | None, Field(default=None, description="Этап строительства (напр. «котлован», «монтаж этажей»).")] = None,
    escrow: Annotated[bool | None, Field(default=None, description="Только объекты через эскроу (true) / без эскроу (false).")] = None,
    limit: Annotated[int, Field(default=20, ge=1, le=100, description="Максимум результатов.")] = 20,
) -> dict[str, Any]:
    """Каталог объектов: ключ ЕИСЖС клиента или честный отказ. Описание методов закрыто."""
    return await _source_or_hosted(
        "list_new_buildings",
        lambda: _call(
            lambda c: c.search_objects(
                region, developer_inn, commissioning_year, stage, escrow, limit
            )
        ),
    )


@mcp.tool
async def get_developer_risk_summary(
    inn: Annotated[str, Field(min_length=1, description="ИНН застройщика.")],
) -> dict[str, Any]:
    """Сводка риска: ключ ЕИСЖС клиента или честный отказ. Описание методов закрыто."""
    return await _source_or_hosted(
        "get_developer_risk_summary",
        lambda: _call(lambda c: c.developer_risk(inn)),
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atomno-mcp-newbuild",
        description=(
            "MCP server: new-build checks on the client's EISZHS contract. "
            "Method spec is closed; no invented exchange."
        ),
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"atomno-mcp-newbuild {__version__}",
        help="Show version and exit.",
    )
    parser.add_argument(
        "--transport",
        "-t",
        choices=_SUPPORTED_TRANSPORTS,
        default=_DEFAULT_TRANSPORT,
        help=f"MCP transport (default: {_DEFAULT_TRANSPORT}).",
    )
    parser.add_argument(
        "--host",
        default=_DEFAULT_HTTP_HOST,
        help=f"Host for http transports (default: {_DEFAULT_HTTP_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_DEFAULT_HTTP_PORT,
        help=f"Port for http transports (default: {_DEFAULT_HTTP_PORT}).",
    )
    parser.add_argument(
        "--log-level",
        "-l",
        choices=_VALID_LOG_LEVELS,
        default=None,
        help="Logging level; overrides MCP_NEWBUILD_LOG_LEVEL (default: INFO).",
    )
    return parser


def _resolve_log_level(cli_value: str | None) -> str:
    if cli_value is not None:
        return cli_value
    env_raw = os.environ.get("MCP_NEWBUILD_LOG_LEVEL")
    if env_raw is None:
        return "INFO"
    env_norm = env_raw.strip().upper()
    if env_norm in _VALID_LOG_LEVELS:
        return env_norm
    raise ValueError(
        f"MCP_NEWBUILD_LOG_LEVEL={env_raw!r} is invalid. "
        f"Allowed: {', '.join(_VALID_LOG_LEVELS)}."
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    try:
        log_level = _resolve_log_level(args.log_level)
    except ValueError as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover

    logging.basicConfig(level=log_level)
    run_kwargs: dict[str, Any] = {"transport": args.transport}
    if args.transport in ("http", "sse", "streamable-http"):
        run_kwargs["host"] = args.host
        run_kwargs["port"] = args.port
    mcp.run(**run_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
