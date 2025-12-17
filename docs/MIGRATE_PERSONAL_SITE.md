# Миграция personal_site на централизованную инфраструктуру

## Контекст

Мы переводим все сервисы на единую инфраструктуру с централизованным Caddy reverse proxy. Это упрощает управление SSL-сертификатами, мониторинг и деплой новых сервисов.

**Текущее состояние:** personal_site имеет собственный Caddy внутри docker-compose, который слушает порты 80/443.

**Целевое состояние:** Глобальный Caddy на сервере проксирует трафик к сервисам. Каждый сервис выставляет только внутренние порты на localhost.

## Что нужно сделать

### 1. Создать `infra/docker-compose.ansible.yml`

Новый compose-файл без Caddy, с портами на localhost:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: personal_site
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    image: ghcr.io/vladmesh/personal_site/backend:latest
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/personal_site
      PYTHONPATH: /app/src
      ADMIN_USERNAME: ${ADMIN_USERNAME:-admin}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:?ADMIN_PASSWORD is required}
      ADMIN_SECRET_KEY: ${ADMIN_SECRET_KEY:?ADMIN_SECRET_KEY is required}
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"  # Только localhost!
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped

  frontend:
    image: ghcr.io/vladmesh/personal_site/frontend:latest
    environment:
      INTERNAL_API_URL: http://backend:8000
      HOST: 0.0.0.0
      PORT: 4321
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "127.0.0.1:4321:4321"  # Только localhost!
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://127.0.0.1:4321/en/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    restart: unless-stopped

  # НЕТ CADDY - используется глобальный

volumes:
  postgres_data:

networks:
  default:
    name: personal_site_network
```

**Ключевые изменения:**
- Убран сервис `caddy`
- Убраны volumes `caddy_data` и `caddy_config`
- Порты backend и frontend биндятся на `127.0.0.1` (не доступны извне)
- Frontend не слушает 80/443

### 2. Обновить GitHub Actions workflow

В `.github/workflows/deploy.yml` изменить шаг деплоя:

**Было:**
```yaml
- name: Copy configs to VPS
  run: |
    scp ... infra/docker-compose.prod.yml ...:/opt/personal_site/docker-compose.yml
    scp ... infra/configs/Caddyfile ...:/opt/personal_site/configs/Caddyfile
```

**Стало:**
```yaml
- name: Copy configs to VPS
  run: |
    scp ... infra/docker-compose.ansible.yml ...:/opt/services/personal_site/docker-compose.yml
```

**Обрати внимание:**
- Путь изменился с `/opt/personal_site` на `/opt/services/personal_site`
- Caddyfile больше не копируется (управляется централизованно)
- Используется `docker-compose.ansible.yml`

### 3. Обновить путь деплоя

Весь деплой теперь идёт в `/opt/services/personal_site/`:

```yaml
- name: Deploy
  run: |
    ssh ... "cd /opt/services/personal_site && \
    echo 'POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}' > .env && \
    echo 'ADMIN_USERNAME=${{ secrets.ADMIN_USERNAME }}' >> .env && \
    echo 'ADMIN_PASSWORD=${{ secrets.ADMIN_PASSWORD }}' >> .env && \
    echo 'ADMIN_SECRET_KEY=${{ secrets.ADMIN_SECRET_KEY }}' >> .env && \
    echo '${{ secrets.GITHUB_TOKEN }}' | docker login ghcr.io -u ${{ github.actor }} --password-stdin && \
    docker compose pull && \
    docker compose up -d && \
    docker image prune -f"
```

## Как будет работать роутинг

Глобальный Caddy на сервере будет настроен так:

```
vladmesh.dev, www.vladmesh.dev {
    encode zstd gzip

    # Admin panel -> backend
    handle /admin* {
        reverse_proxy localhost:8000
    }

    # Всё остальное -> frontend
    handle {
        reverse_proxy localhost:4321
    }

    # Security headers
    header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    header X-Content-Type-Options "nosniff"
    header Referrer-Policy "strict-origin-when-cross-origin"
}
```

Эта конфигурация генерируется автоматически из `prod_infra/ansible/services.yml`.

## Чеклист

- [ ] Создать `infra/docker-compose.ansible.yml`
- [ ] Обновить `.github/workflows/deploy.yml`:
  - [ ] Изменить путь на `/opt/services/personal_site`
  - [ ] Убрать копирование Caddyfile
  - [ ] Использовать `docker-compose.ansible.yml`
- [ ] Проверить что GitHub Secrets содержат все нужные переменные
- [ ] После мержа — проверить что сайт доступен по https://vladmesh.dev

## Порты

| Сервис | Внутренний порт | Внешний доступ |
|--------|-----------------|----------------|
| frontend | 4321 | localhost:4321 → Caddy → vladmesh.dev |
| backend | 8000 | localhost:8000 → Caddy → vladmesh.dev/admin* |
| postgres | 5432 | Нет (только внутри docker network) |


