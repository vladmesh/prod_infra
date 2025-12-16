# Production Server Infrastructure

Ansible playbooks для настройки и управления production сервером. Идемпотентные - можно запускать на голом сервере или на уже настроенном.

## Что делает

- **Security**: SSH hardening (отключен root, только ключи), UFW firewall, fail2ban
- **Docker**: Docker CE + Compose plugin
- **Caddy**: Reverse proxy с автоматическими SSL сертификатами
- **Backup**: Restic + cron для бэкапов
- **Monitoring**: Node exporter для метрик железа

## Быстрый старт

```bash
cd ansible

# 1. Установить зависимости
make install

# 2. Настроить inventory (указать IP сервера)
vim inventory/prod.ini

# 3. Первый запуск на свежем сервере (от root)
make bootstrap

# 4. Полная настройка
make deploy
```

## Структура

```
prod_infra/
├── README.md
├── plan.md              # планы и заметки
└── ansible/
    ├── ansible.cfg
    ├── Makefile
    ├── requirements.yml
    ├── services.yml     # сервисы для Caddy proxy
    ├── inventory/
    │   └── prod.ini
    ├── group_vars/
    │   └── all.yml
    ├── playbooks/
    │   ├── bootstrap.yml
    │   └── site.yml
    └── roles/
        ├── common/      # базовые пакеты, deploy user
        ├── security/    # SSH, firewall, fail2ban
        ├── docker/      # Docker + Compose
        ├── caddy/       # reverse proxy
        ├── backup/      # restic бэкапы
        └── monitoring/  # node_exporter
```

## Конфигурация

### Добавление сервера

`ansible/inventory/prod.ini`:
```ini
[prod]
myserver ansible_host=1.2.3.4

[prod:vars]
ansible_user=deploy
```

### Добавление сервисов для проксирования

`ansible/services.yml`:
```yaml
services:
  - name: myapp
    domain: myapp.example.com
    upstream: "localhost:8080"
    
  - name: api
    domain: api.example.com
    upstream: "localhost:3000"
```

### Настройка бэкапов

`ansible/group_vars/all.yml`:
```yaml
backup_enabled: true
backup_repository: "s3:s3.amazonaws.com/my-backup-bucket"
backup_paths:
  - /opt/services
  - /opt/caddy
```

Пароль для restic хранить в ansible-vault:
```bash
ansible-vault encrypt_string 'my-secret-password' --name 'backup_password'
```

### Изменение портов firewall

`ansible/group_vars/all.yml`:
```yaml
firewall_allowed_ports:
  - "22/tcp"
  - "80/tcp"
  - "443/tcp"
  - "9100/tcp"  # node_exporter (если нужен внешний доступ)
```

## Команды

| Команда | Описание |
|---------|----------|
| `make install` | Установить ansible collections |
| `make bootstrap` | Первый запуск на свежем сервере (от root) |
| `make deploy` | Полный деплой (от deploy user) |
| `make check` | Dry run - показать что изменится |
| `make syntax` | Проверить синтаксис playbooks |

## Порядок первого запуска

1. Получить доступ к серверу по SSH как root
2. Убедиться что локальный SSH ключ `~/.ssh/id_ed25519.pub` существует
3. `make install` - установить зависимости
4. `make bootstrap` - создаст пользователя deploy с sudo
5. `make deploy` - настроит всё остальное

После этого root доступ будет отключен, вход только по ключу через пользователя deploy.

## Мониторинг

Node exporter доступен на порту 9100. Метрики можно собирать внешним Prometheus:

```yaml
scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['your-server:9100']
```

## Troubleshooting

**Не могу подключиться после bootstrap:**
- Убедись что SSH ключ добавлен правильно
- Проверь что используешь пользователя deploy: `ssh deploy@server`

**Fail2ban заблокировал:**
```bash
# На сервере
sudo fail2ban-client set sshd unbanip YOUR_IP
```

**Проверить статус firewall:**
```bash
sudo ufw status verbose
```
