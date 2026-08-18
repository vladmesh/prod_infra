# prod_infra

> **Поглощён кодген-оркестратором.** Ansible-часть переехала в
> [vladmesh/codegen_orchestrator](https://github.com/vladmesh/codegen_orchestrator), в
> [`services/infra-service/ansible/`](https://github.com/vladmesh/codegen_orchestrator/tree/main/services/infra-service/ansible).
> Этот репозиторий заморожен и остаётся как история; правки идут туда.

Идемпотентные Ansible-плейбуки для настройки production-сервера: SSH hardening и UFW с fail2ban,
Docker CE с compose-плагином, Caddy как reverse proxy с автоматическим TLS, restic для бэкапов,
node exporter для метрик железа.

Отдельным репозиторием это прожило месяц. Инвентарь с самого начала ходил в API оркестратора
(`api_inventory.py`, переменная `ORCHESTRATOR_API_URL`), то есть инфраструктура и так была его
частью — держать её в стороне от кода, который ей управляет, смысла не было.

## Где искать

Роли переехали как есть (`common`, `docker`, `caddy`, `backup`, `monitoring`, `security`,
`services`) и с тех пор развивались: добавились `deploy_target` и `qa_identity`, плейбуки
провижининга и health-check, promtail в мониторинге. Динамический инвентарь научился новому
`ORCHESTRATOR_API_BASE_URL`.

Ничего, чего нет в оркестраторе, здесь не осталось.

---

Инвентарь с реальным хостом (`ansible/inventory/prod.ini`) в этом репозитории никогда не хранился:
в дереве лежит только `prod.ini.example` с плейсхолдером, а история вычищена 19.06.2026.
