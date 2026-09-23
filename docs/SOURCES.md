# Источники и сторонние компоненты

## Задание и данные

- [Официальное ТЗ Career Quest](https://docs.google.com/document/d/18SlxWxz_Vj_eag_UfEQ6t6g59jCxGTgu5x4QoylDbqI/edit?tab=t.0).
- Стартовый набор `career_quest_dataset`, версия 1.0, срез 2026-10-01. Все люди и компании вымышлены; использование ограничено рамками хакатона по ТЗ. Открытая лицензия на публикацию вне хакатона не заявляется.
- `docs/fixtures` — собственные синтетические дополнения команды в той же схеме; это не профили жюри.
- Положение сохранено в `HACKATHON_RULES.md`.

## Библиотеки

Версии и лицензии библиотек ниже проверены по метаданным установленных пакетов. Полный набор Python-зависимостей фиксирует `backend/requirements.lock`, JavaScript — `frontend/package-lock.json`.

| Компонент | Версия | Лицензия / источник |
| --- | --- | --- |
| FastAPI | 0.141.1 | MIT, https://github.com/fastapi/fastapi |
| Uvicorn | 0.53.0 | BSD-3-Clause, https://github.com/encode/uvicorn |
| SQLAlchemy | 2.0.54 | MIT, https://github.com/sqlalchemy/sqlalchemy |
| Alembic | 1.20.0 | MIT, https://github.com/sqlalchemy/alembic |
| asyncpg | 0.31.0 | Apache-2.0, https://github.com/MagicStack/asyncpg |
| Pydantic | 2.13.5 | MIT, https://github.com/pydantic/pydantic |
| redis-py | 8.1.0 | MIT, https://github.com/redis/redis-py |
| OpenAI Python SDK | 3.19.0 | Apache-2.0, https://github.com/openai/openai-python |
| argon2-cffi | 25.1.0 | MIT, https://github.com/hynek/argon2-cffi |
| itsdangerous | 2.2.0 | BSD, https://github.com/pallets/itsdangerous |
| Next.js | 16.3.6 | MIT, https://github.com/vercel/next.js |
| React | 19.3.0 | MIT, https://github.com/facebook/react |
| TypeScript | 5.9.3 | Apache-2.0, https://github.com/microsoft/TypeScript |
| openapi-typescript | 7.13.0 | MIT, https://github.com/openapi-ts/openapi-typescript |
| openpyxl | 3.1.5 | MIT, https://openpyxl.readthedocs.io/en/stable/ |
| et_xmlfile | 2.0.0 | MIT, https://foss.heptapod.net/openpyxl/et_xmlfile |
| defusedxml | 0.7.1 | PSF, https://github.com/tiran/defusedxml |
| Playwright | 1.63.0 | Apache-2.0, https://github.com/microsoft/playwright |

Контейнеры: Python 3.12.13-slim, Node.js 22.22.1-alpine, PostgreSQL 17.7-alpine, Redis 7.4.7-alpine. Redis server и redis-py имеют разные лицензии: ветка Redis 7.4 поставляется с выбором RSALv2/SSPL, как указано в [README версии 7.4.7](https://github.com/redis/redis/blob/7.4.7/README.md) и [LICENSE](https://github.com/redis/redis/blob/7.4.7/LICENSE.txt). Исходники Redis не изменяются; используется отдельный локальный контейнер.

## AI и происхождение реализации

- Провайдер модели — OpenAI API, конфигурируемая модель `gpt-4.1-mini-2025-04-14`. Это внешний сервис, а не поставляемые открытые веса модели.
- [Responses API и структурированные ответы](https://developers.openai.com/api/docs/guides/structured-outputs).
- AI получает обезличенные синтетические признаки, допустимые варианты и агрегаты истории. Код выбирает допустимые события; модель ранжирует их; сервер проверяет ответ и формирует фактическое обоснование.
- Исходники приложения и тесты подготовлены с помощью Codex в соревновательный период. До реализации были подготовлены документы контекста и архитектурный промпт; готовое приложение заранее не использовалось.
- Готовые продуктовые шаблоны, сторонние изображения и веб-шрифты не используются. Интерфейс выполнен на CSS Modules и системных шрифтах.
- Собственные шаблоны импорта находятся в `backend/app/features/data_import/templates`. Справочники взяты из стартового набора; пример сотрудника синтетический. Excel подготовлен инструментом Spreadsheets / artifact-tool; он не является runtime-зависимостью приложения. Сервер читает .xlsx через openpyxl, не исполняет формулы. [Документация чтения](https://openpyxl.readthedocs.io/en/stable/tutorial.html#loading-from-a-file).


## Дополнительные материалы к активностям

Добавлены 23.09.2026: ссылки на открытые материалы первоисточников для 30 активностей. Храним только адреса и собственные короткие описания; полные тексты не копируются. Материалы на английском, служат дополнительным чтением или подготовкой, не заменяют программу курса. Для обязательных внутренних программ и отдельных HR/продажных тем ссылки не подставляются без подходящего проверенного источника.

- [Основы архитектуры приложений](https://learn.microsoft.com/en-us/azure/architecture/guide/) — Microsoft Learn.
- [Как писать понятную техническую документацию](https://developers.google.com/tech-writing) — Google.
- [Практическое знакомство с Kubernetes](https://kubernetes.io/docs/tutorials/kubernetes-basics/) — Kubernetes.
- [Распространенные уязвимости веб-приложений](https://owasp.org/projects/top-ten) — OWASP.
- [Типы и обобщения в Python](https://docs.python.org/3/library/typing.html) — Python Software Foundation.
- [Руководство по системе типов TypeScript](https://www.typescriptlang.org/docs/handbook/intro.html) — TypeScript.
- [Производительность веб-приложений](https://web.dev/learn/performance) — Google · web.dev.
- [Как создавать доступные интерфейсы](https://web.dev/learn/accessibility/) — Google · web.dev.
- [Управление состоянием в React](https://react.dev/learn/managing-state) — React.
- [Приемы написания надежных тестов](https://playwright.dev/docs/best-practices) — Playwright.
- [Первые нагрузочные тесты с k6](https://grafana.com/docs/k6/latest/get-started/) — Grafana.
- [Справочник по статистическим методам](https://www.itl.nist.gov/div898/handbook/) — NIST / SEMATECH.
- [Оконные функции SQL](https://www.postgresql.org/docs/current/tutorial-window.html) — PostgreSQL.
- [Как сделать дашборд понятным](https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips) — Microsoft Learn.
- [Первые модели в scikit-learn](https://scikit-learn.org/stable/getting_started.html) — scikit-learn.
- [Схема «звезда» для аналитики](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema) — Microsoft Learn.
- [Подготовка и проведение интервью с клиентом](https://www.atlassian.com/team-playbook/plays/customer-interview) — Atlassian.
- [Как расставить приоритеты](https://www.atlassian.com/team-playbook/plays/prioritize-tasks-how-to) — Atlassian.
- [Как подготовить учебное занятие](https://carpentries.github.io/instructor-training/) — The Carpentries.
- [Последовательный поиск причин сбоя](https://sre.google/sre-book/effective-troubleshooting/) — Google SRE.
- [Советы по публичным выступлениям](https://www.toastmasters.org/resources/public-speaking-tips) — Toastmasters International.
- [Как помогать коллегам в роли наставника](https://www.atlassian.com/blog/leadership/how-to-be-a-good-mentor-for-your-whole-team) — Atlassian.
- [Роли и ответственность в команде](https://www.atlassian.com/team-playbook/plays/roles-and-responsibilities) — Atlassian.
- [Как сформулировать проблему перед поиском решения](https://www.atlassian.com/team-playbook/plays/problem-framing) — Atlassian.
