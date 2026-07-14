"""FastMCP entrypoint для atomno-mcp-newbuild (тонкий клиент).

Все тулы проксируют к hosted-бэкенду Atomno Labs (тариф Pro, ключ
MCP_NEWBUILD_API_KEY): check_developer, get_project_declaration, check_escrow,
check_construction_permit, list_new_buildings, get_developer_risk_summary.
Каждый ответ несёт disclaimer/source. Данные — СПРАВОЧНЫЕ, из официального
ЕИСЖС/наш.дом.рф; не инвестиционная рекомендация (см. spec, разделы 8-9).
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
        "Check Russian new-build developers and construction projects for AI "
        "agents, straight from the official ЕИСЖС / наш.дом.рф data (214-ФЗ): "
        "developer profile by INN/OGRN, project declaration, escrow scheme and "
        "authorised bank, construction permit with deadline-shift history, a "
        "filterable catalogue of buildings under construction, and a deterministic "
        "developer risk summary. All tools go through the Atomno Labs hosted API "
        "and need a Pro key (MCP_NEWBUILD_API_KEY). Every answer carries a "
        "disclaimer and a source. The data is advisory, not an investment "
        "recommendation — verify with the primary source before a deal. Get a key "
        "at https://atomno-mcp.ru/pricing#newbuild-pro."
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


def _no_token_hint() -> dict[str, Any]:
    return {
        "error": "missing_token",
        "message_ru": (
            "Не задан MCP_NEWBUILD_API_KEY. Проверка новостроек и застройщиков — "
            "платная (тариф Pro). Ключ: https://atomno-mcp.ru/pricing#newbuild-pro"
        ),
        "disclaimer": DISCLAIMER,
    }


async def _hosted_call(name: str, coro_factory) -> dict[str, Any]:
    if not _settings.has_token:
        return _no_token_hint()
    try:
        result = await coro_factory()
        result.setdefault("disclaimer", DISCLAIMER)
        return result
    except BackendError as exc:
        if exc.status_code == 401:
            return _no_token_hint()
        logger.warning("%s backend %s: %s", name, exc.status_code, exc.detail)
        return {"error": "backend_error", "status": exc.status_code, "message": exc.detail}
    except NewbuildError as exc:
        logger.warning("%s failed: %s", name, exc)
        return {"error": "unavailable", "message": str(exc)}


async def _call(fn) -> dict[str, Any]:
    client = await _get_client()
    return await fn(client)


@mcp.tool
async def check_developer(
    ident: Annotated[str, Field(min_length=1, description="ИНН или ОГРН застройщика (юрлица).")],
) -> dict[str, Any]:
    """Карточка застройщика из ЕИСЖС по ИНН/ОГРН: реквизиты, реестр застройщиков, объекты, число проблемных, фин.состояние по 214-ФЗ. Тариф Pro."""
    return await _hosted_call(
        "check_developer",
        lambda: _call(lambda c: c.developer(ident)),
    )


@mcp.tool
async def get_project_declaration(
    object_id: Annotated[str, Field(min_length=1, description="Идентификатор объекта (строящегося дома/ЖК) в ЕИСЖС.")],
) -> dict[str, Any]:
    """Проектная декларация объекта: параметры дома, застройщик, банк, планируемый срок ввода, ключевые площади, изменения декларации. Тариф Pro."""
    return await _hosted_call(
        "get_project_declaration",
        lambda: _call(lambda c: c.declaration(object_id)),
    )


@mcp.tool
async def check_escrow(
    object_id: Annotated[str, Field(min_length=1, description="Идентификатор объекта в ЕИСЖС.")],
) -> dict[str, Any]:
    """Схема привлечения средств по объекту: используются ли эскроу-счета (214-ФЗ), уполномоченный банк, признак эскроу/без эскроу/спецсчёт. Тариф Pro."""
    return await _hosted_call(
        "check_escrow",
        lambda: _call(lambda c: c.escrow(object_id)),
    )


@mcp.tool
async def check_construction_permit(
    object_id: Annotated[str, Field(min_length=1, description="Идентификатор объекта в ЕИСЖС.")],
) -> dict[str, Any]:
    """Разрешение на строительство по объекту: РНС, заявленный и фактический этап, срок ввода, история переноса сроков (PRO). Тариф Pro."""
    return await _hosted_call(
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
    """Поиск/каталог строящихся объектов с фильтрами (регион, застройщик, срок ввода, стадия, эскроу). Точка входа «что строится» + сравнение. Тариф Pro."""
    return await _hosted_call(
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
    """Детерминированная сводка риска застройщика по портфелю: доля проблемных объектов, средний сдвиг сроков (мес.), доля без эскроу, введено в срок. Нейтральные формулировки, справочно. Тариф Pro."""
    return await _hosted_call(
        "get_developer_risk_summary",
        lambda: _call(lambda c: c.developer_risk(inn)),
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atomno-mcp-newbuild",
        description=(
            "MCP server: Russian new-build developer & project checks via "
            "ЕИСЖС/наш.дом.рф (214-ФЗ)."
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
