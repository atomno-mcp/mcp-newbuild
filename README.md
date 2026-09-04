<!-- mcp-name: io.github.atomno-mcp/mcp-newbuild -->

# atomno-mcp-newbuild

Клиент для запросов по новостройкам и застройщикам. ЕИСЖС и наш.дом.рф ещё не подключены: ответ сообщает, что источник подключается, и не выдаёт пустую карточку как «объект не найден».

New-build MCP client. EISZHS / nash.dom.rf are not connected yet.

> Это **не** инвестиционная рекомендация. Сейчас источник не подключён.

## Что умеет сейчас

- Принимает запрос на карточку застройщика, декларацию, эскроу, разрешение, каталог и сводку риска.
- Отвечает честно: `ready: false` и причина — источник ещё не подключён.
- Не подменяет отказ пустым списком объектов.

## Что не подключено

- ЕИСЖС / наш.дом.рф (застройщики, декларации, эскроу, разрешения, каталог)

## Быстрый старт

```bash
pipx install atomno-mcp-newbuild
# или: uvx atomno-mcp-newbuild
```

Cursor / Claude Desktop (`mcp.json` / `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "newbuild": {
      "command": "uvx",
      "args": ["atomno-mcp-newbuild"],
      "env": { "MCP_NEWBUILD_API_KEY": "<ваш-ключ-Pro>" }
    }
  }
}
```

## Переменные окружения

| Переменная | Описание | Обязательна |
|---|---|---|
| `MCP_NEWBUILD_API_KEY` | Ключ Pro (заголовок X-API-Key). [Получить](https://atomno-mcp.ru/pricing#newbuild-pro) | да |
| `MCP_NEWBUILD_API_BASE` | URL hosted-бэкенда (по умолчанию — прод) | нет |
| `MCP_NEWBUILD_TIMEOUT` | Таймаут HTTP, сек (default 30) | нет |
| `MCP_NEWBUILD_LOG_LEVEL` | Уровень логирования (DEBUG/INFO/WARNING/ERROR, default WARNING) | нет |

## Тулы

| Тул | Вход | Что отвечает сейчас |
|---|---|---|
| `check_developer` | ident (ИНН/ОГРН) | `ready: false` — ЕИСЖС не подключён |
| `get_project_declaration` | object_id | `ready: false` — ЕИСЖС не подключён |
| `check_escrow` | object_id | `ready: false` — ЕИСЖС не подключён |
| `check_construction_permit` | object_id | `ready: false` — ЕИСЖС не подключён |
| `list_new_buildings` | region?, developer_inn?, commissioning_year?, stage?, escrow?, limit? | `ready: false` — ЕИСЖС не подключён |
| `get_developer_risk_summary` | inn | `ready: false` — ЕИСЖС не подключён |

Каждый ответ содержит `source`, `checked_at` и `disclaimer`.

## Дисклеймер

ЕИСЖС / наш.дом.рф ещё не подключены. Это **не** инвестиционная рекомендация.
Не аффилировано с ДОМ.РФ и ЕИСЖС.

## Лицензия

MIT © Atomno
