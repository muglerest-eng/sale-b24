# TimeWeb VPS: подготовка под MAX (до и после модерации)

Проект уже **только под MAX** — Telegram не используется. Пока бот на модерации, поднимаем сервер и Битрикс; MAX подключаем в конце.

## Фаза 1 — сейчас (бот на модерации)

### 1. VPS в TimeWeb

- ОС: **Ubuntu 22.04 / 24.04**
- Минимум: 1 vCPU, 1 GB RAM
- Привяжите **домен** (A-запись на IP VPS)

### 2. Загрузка кода

Без GitHub — архив или SFTP в `/opt/sale_b24`:

```bash
# на локальной машине
cd sale_b24
tar czf sale_b24.tar.gz --exclude=.venv --exclude=__pycache__ app deploy scripts requirements.txt .env.example README.md
scp sale_b24.tar.gz root@ВАШ_IP:/opt/
# на сервере
mkdir -p /opt/sale_b24 && tar xzf /opt/sale_b24.tar.gz -C /opt/sale_b24
```

### 3. Автонастройка сервера

```bash
cd /opt/sale_b24
DOMAIN=bot.ваш-домен.ru sudo -E bash deploy/setup_vps.sh
```

### 4. `.env` на сервере

```bash
nano /opt/sale_b24/.env
systemctl restart sale-b24
```

Заполните **сразу**:

- Битрикс (домен, токены webhooks, UF-поля)
- `MAX_WEBHOOK_SECRET` — придумайте (5+ символов, латиница/цифры/`-_`)
- `MAX_SUBSCRIBE_CODE` — код для `/start`
- `MAX_BOT_TOKEN` — можно вставить уже сейчас (если выдан)

### 5. Битрикс24

| Webhook | URL / событие |
|---------|----------------|
| Исходящий | `https://bot.ваш-домен.ru/bitrix/webhook` → **ONCRMLEADADD** |
| Входящий | права CRM, URL в `BITRIX_INCOMING_WEBHOOK_URL` |

### 6. Проверка без MAX

```bash
cd /opt/sale_b24
source .venv/bin/activate
python scripts/check_infrastructure.py --public-url https://bot.ваш-домен.ru --skip-max
```

Ожидаем: OK на `/health`, ENV, Битрикс.

---

## Фаза 2 — после модерации MAX

### 1. Токен бота

Кабинет партнёра MAX → бот → токен → в `MAX_BOT_TOKEN`, перезапуск:

```bash
systemctl restart sale-b24
```

### 2. Активация webhook MAX

```bash
cd /opt/sale_b24 && source .venv/bin/activate
python scripts/activate_max.py https://bot.ваш-домен.ru --bot-username НикБота
```

### 3. Подписка менеджеров

В MAX: `/start ВАШ_КОД` или deeplink из вывода скрипта.

### 4. Полная проверка

```bash
python scripts/check_infrastructure.py --public-url https://bot.ваш-домен.ru
```

### 5. Тест

Создайте тестовый лид в CRM → сообщение должно прийти в MAX.

---

## Требования MAX к серверу

| Требование | Как у нас |
|------------|-----------|
| HTTPS, порт 443 | nginx + Let's Encrypt |
| Доверенный сертификат | certbot |
| Webhook ≤ 30 сек | FastAPI отвечает сразу, обработка в фоне |
| `Authorization` заголовок | `MaxClient` |
| `X-Max-Bot-Api-Secret` | проверка в `/max/webhook` |

API: `https://platform-api2.max.ru`

---

## Полезные команды

```bash
journalctl -u sale-b24 -f          # логи
systemctl restart sale-b24
curl -s https://bot.ваш-домен.ru/health
cat /opt/sale_b24/data/subscribers.json   # кто подписан
```
