# Changelog

Все заметные изменения фиксируются здесь. Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версии — [SemVer](https://semver.org/lang/ru/).

## [0.1.0] — 2026-07-04

### Added

- Тонкий MCP-клиент `atomno-mcp-newbuild` (open-core: публичный клиент + приватный hosted-сервер).
- 6 тулов через hosted API (тариф Pro): `check_developer`, `get_project_declaration`,
  `check_escrow`, `check_construction_permit`, `list_new_buildings`, `get_developer_risk_summary`.
- Проверка новостроек и застройщиков РФ по официальным данным ЕИСЖС/наш.дом.рф (214-ФЗ).
- Обязательный дисклеймер о справочном характере данных (не инвестиционная рекомендация) в каждом ответе.
- CLI argparse (`--help/--version/--transport/--host/--port/--log-level`), env `MCP_NEWBUILD_*`.
- Метаданные для офиц. MCP Registry (`server.json` + workflow OIDC + маркер `mcp-name`), `glama.json`, `Dockerfile`.
