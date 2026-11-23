# Changelog

Все заметные изменения фиксируются здесь. Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии — [SemVer](https://semver.org/lang/ru/).

## [0.1.6] — 2026-11-23

### Fixed

- Обновлён адрес автора Python-пакета.

## [0.1.5] — 2026-09-04

### Added

- Переменные `MCP_NEWBUILD_EISZHS_CLIENT_ID` и `MCP_NEWBUILD_EISZHS_CLIENT_SECRET` для договора клиента с ЕИСЖС.

### Changed

- Тулы принимают учётку клиента ЕИСЖС. Без учётки отвечают `source_not_configured`. Если спецификация методов закрыта договором — `spec_closed`.
- Неверный ключ нашего размещения отвечает `invalid_credentials`.

## [0.1.0] — 2026-07-04

### Added

- Тонкий MCP-клиент `atomno-mcp-newbuild` (публичный клиент + hosted corporate API, тариф Pro).
- 6 тулов через hosted API (тариф Pro): `check_developer`, `get_project_declaration`,
  `check_escrow`, `check_construction_permit`, `list_new_buildings`, `get_developer_risk_summary`.
- Проверка новостроек и застройщиков РФ по официальным данным ЕИСЖС/наш.дом.рф (214-ФЗ).
- Обязательный дисклеймер о справочном характере данных (не инвестиционная рекомендация) в каждом ответе.
- CLI argparse (`--help/--version/--transport/--host/--port/--log-level`), env `MCP_NEWBUILD_*`.
- Метаданные для офиц. MCP Registry (`server.json` + workflow OIDC + маркер `mcp-name`), `glama.json`, `Dockerfile`.
