# Task3. Целевая облачная архитектура

## Резюме

- **As-Is:** схема с Wiki (Артефакт 1) невалидна. Она показывает real-time REST к SAP, которого нет: на деле ночной XML по FTP. На ней нет ОФД, процессинга, Promo Engine и Smart Fulfillment, а парк терминалов показан однородным. Исправленная схема — [02-as-is.md](02-as-is.md).
- **To-Be:** собственный Cloud POS на PaaS Yandex Cloud ([ADR-006](adr/ADR-006-own-cloud-pos.md)). В магазине — Android-планшет с Web POS (PWA) и Edge Agent, ККТ АТОЛ / Штрих-М, PIN-pad и роутер с LTE-резервом. Сервера и БД нет.
- **Разнородное «железо»:** HAL в Edge Agent на планшете с едиными интерфейсами `IFiscalPrinter` / `IPaymentTerminal` и плагинами вендоров (Сбер ARCUS-2, Альфа, Ingenico, Verifone, АТОЛ, Штрих-М). Облачный Payment Gateway маршрутизирует платежи к эквайрерам и сверяет их. Новый терминал подключается плагином и профилем, без пересборки кассы ([ADR-007](adr/ADR-007-edge-agent-hal.md)).
- **Офлайн:** наличные с фискальным чеком, лояльность с отложенным начислением и лимитом списания, до 72 часов автономно ([ADR-008](adr/ADR-008-offline-mode.md)). Синхронизация — outbox с идемпотентными ключами, затем дельты справочников по версиям, офлайн-чек фиксируется как неизменяемый факт ([04-offline-sync.md](04-offline-sync.md)).

## Состав результата

| Файл | Содержание |
| --- | --- |
| [01-goal.md](01-goal.md) | Постановка задачи |
| [02-as-is.md](02-as-is.md) | Проверка Артефакта 1, исправленная схема As-Is C4 Containers ([as-is-containers.puml](as-is-containers.puml) → `as-is-containers.png`), проблемы As-Is |
| [03-to-be-architecture.md](03-to-be-architecture.md) | HLD: компоненты Edge и Cloud ([to-be-hld.puml](to-be-hld.puml) → `to-be-hld.png`), HAL / Payment Gateway ([hal-components.puml](hal-components.puml) → `hal-components.png`), переход от толстого клиента к Cloud-Native |
| [04-offline-sync.md](04-offline-sync.md) | Офлайн-стратегия, кэш, механизм синхронизации и разрешение конфликтов ([offline-sync.puml](offline-sync.puml) → `offline-sync.png`) |
| [adr/ADR-006-own-cloud-pos.md](adr/ADR-006-own-cloud-pos.md) | Собственный Cloud POS вместо SaaS-кассы |
| [adr/ADR-007-edge-agent-hal.md](adr/ADR-007-edge-agent-hal.md) | Web POS + Edge Agent (HAL), Payment Gateway, политика оборудования |
| [adr/ADR-008-offline-mode.md](adr/ADR-008-offline-mode.md) | Объём и длительность офлайн-режима |

Диаграммы — C4-PlantUML (stdlib) и sequence PlantUML. Пересборка (из каталога `Task3`):

```bash
java -jar "$TEMP/plantuml.jar" -charset UTF-8 -tpng as-is-containers.puml to-be-hld.puml hal-components.puml offline-sync.puml
```

Используются решения Task1 и Task2: [ADR-001](../Task1/adr/ADR-001-hq-in-cloud.md) (Yandex Cloud), [ADR-002](../Task1/adr/ADR-002-scope-all-stores.md) (в магазине только физика), [ADR-003](../Task1/adr/ADR-003-sap-to-1c.md) (1С:ERP), [ADR-004](../Task2/adr/ADR-004-onboarding-scope-and-channel.md) (публикация ассортимента событием в Cloud POS), [Sourcing Strategy](../Task1/04-sourcing-strategy.md) 1.2, 1.3, 5.3, 9.1.

## Реестр разрывов и противоречий в постановке

Нумерация продолжает [реестр Task2](../Task2/README.md).

| № | Разрыв / противоречие | Источники | Как закрыто |
| --- | --- | --- | --- |
| G20 | Task1 выбирает SaaS-кассу, а Task3 требует собственную Cloud-Native-архитектуру с HAL и офлайн-режимом | Task1 Sourcing 1.1 vs постановка Task3 | [ADR-006](adr/ADR-006-own-cloud-pos.md): собственный Cloud POS на PaaS; ОФД, лояльность и эквайринг остаются SaaS |
| G21 | Касса — тонкий клиент, но браузер не работает с USB / COM и драйверами устройств | Постановка Task3 | [ADR-007](adr/ADR-007-edge-agent-hal.md): Edge Agent на том же планшете, Local API на localhost |
| G22 | Task1 вводит стандартный комплект, Task3 требует работать с разнородными ФР и терминалами | Task1 Sourcing 5.3 vs постановка Task3 | [ADR-007](adr/ADR-007-edge-agent-hal.md): ФР меняются на АТОЛ / Штрих-М при перерегистрации ККТ; терминалы остаются и подключаются через HAL и Payment Gateway |
| G23 | Постановка требует офлайн только для наличных, а INC-8402 показывает потери из-за отказа в лояльности | Постановка Task3 vs INC-8402 | [ADR-008](adr/ADR-008-offline-mode.md): отложенное начисление, списание в пределах кэшированного баланса с лимитом |
| G24 | Артефакт 1 неполон и нарушает нотацию: `C4Context` вместо Containers, устройства как контейнеры, нет ОФД, процессинга, FTP, Promo Engine, Smart Fulfillment | Артефакт 1 vs Артефакты 2-3, описание кейса | Исправленная схема As-Is ([02-as-is.md](02-as-is.md), таблица 2.1) |
| G25 | Не определено, принимаются ли карты без интернета | Постановка Task3 | Допущение: только если у терминала свой канал связи; офлайн-авторизация по floor limit не используется ([ADR-008](adr/ADR-008-offline-mode.md)) |
| G26 | Не задана длительность автономной работы | Постановка Task3 | Допущение: целевая — 72 часа; жёсткий предел — 30 дней до блокировки ФН без передачи в ОФД ([ADR-008](adr/ADR-008-offline-mode.md)) |

## Допущения

- Планшеты кассы — Android, управляются MDM (Task1, 5.3). iOS не используется: там недоступны фоновый локальный сервис и USB-драйверы, без которых Edge Agent не работает.
- Плагины Edge Agent для терминалов разрабатываются по SDK и протоколам вендоров или банков. Их наличие для Android подтверждается на пилоте; если SDK для модели нет, терминал заменяется при онбординге.
- Объёмы кэша (~10 000 SKU) и чеков — по средним значениям Task2; уточняются на пилоте.
- Облачная ККТ не используется: для розницы с наличными 54-ФЗ требует ККТ в месте расчёта.
