# Timeweb App Platform (Backend → FastAPI)

## Переменные окружения

Те же, что были на Railway (Telegram заменён на MAX):

```env
BITRIX24_CLIENT_ID=local.xxxxxxxxxxxx.xxxxxxxx
BITRIX24_CLIENT_SECRET=...
BITRIX24_HANDLER_URL=https://ВАШ-APP.timeweb.cloud/webhook/bitrix24

MANGO_CALL_URL_TEMPLATE=https://integration-webhook.mango-office.ru/...&TelNumbr={phone}

MAX_BOT_TOKEN=...
MAX_WEBHOOK_SECRET=...
MAX_SUBSCRIBE_CODE=482917
MAX_API_BASE_URL=https://platform-api2.max.ru

BITRIX_FIELD_CITY=UF_CRM_...
BITRIX_FIELD_VISA_QUESTIONS=UF_CRM_...

DATA_DIR=/tmp/sale_b24_data
```

**Важно:** после деплоя замените в `BITRIX24_HANDLER_URL` домен Railway на URL Timeweb и обновите **Handler URL** в настройках локального приложения Битрикс24.

## Настройки App Platform

Два варианта (достаточно одного):

### Вариант A — Docker (если платформа требует Dockerfile)

В репозитории есть `Dockerfile` — выберите деплой через Docker / Dockerfile.

### Вариант B — FastAPI без Docker

| Поле | Значение |
|------|----------|
| Тип | Backend → FastAPI |
| Сборка | `pip3 install --upgrade -r requirements.txt` |
| Запуск | `uvicorn main:app --host 0.0.0.0 --port 8000` |
| Health check | `/health` |

## Битрикс24

В локальном приложении handler должен совпадать с путём из `BITRIX24_HANDLER_URL`:
`/webhook/bitrix24`

Событие: **ONCRMLEADADD** (лид создан).

REST-запросы идут через `access_token` из события — отдельный входящий webhook **не нужен**.

## MAX после модерации

```bash
python scripts/activate_max.py https://ВАШ-APP.timeweb.cloud --bot-username НикБота
```

Подписка: `/start КОД` в боте MAX.
