# Bitrix24 → MAX: уведомления о новых лидах

Сервис принимает события локального приложения Битрикс24 (`ONCRMLEADADD`), загружает лид через OAuth-токен из события и отправляет текст подписанным пользователям бота в MAX. Опционально — обратный звонок Mango Office.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `BITRIX24_CLIENT_ID` | ID локального приложения (`local....`) |
| `BITRIX24_CLIENT_SECRET` | Секрет приложения, refresh OAuth |
| `BITRIX24_HANDLER_URL` | Полный URL handler (путь → маршрут FastAPI) |
| `BITRIX24_APPLICATION_TOKEN` | Опционально: строгая проверка событий |
| `MANGO_CALL_URL_TEMPLATE` | Опционально: URL с `{phone}` для Mango |
| `MAX_BOT_TOKEN` | Токен бота MAX |
| `MAX_WEBHOOK_SECRET` | Секрет webhook MAX |
| `MAX_SUBSCRIBE_CODE` | Код подписки `/start` |
| `BITRIX_FIELD_CITY` | UF-поле «город» |
| `BITRIX_FIELD_VISA_QUESTIONS` | UF-поле квиза по визе |

Пример — в `.env.example`.

## Битрикс24

Handler в приложении = путь из `BITRIX24_HANDLER_URL`, по умолчанию:

```
POST https://ваш-домен/webhook/bitrix24
```

Событие: **Лид создан** (`ONCRMLEADADD`).

Отдельный входящий webhook **не требуется** — REST через `auth.access_token` из события.

## MAX

1. `python scripts/activate_max.py https://ваш-домен --bot-username НикБота`
2. В MAX: `/start ВАШ_КОД`

## Деплой

- **Timeweb App Platform:** [`deploy/TIMEWEB_APP.md`](deploy/TIMEWEB_APP.md)
- **Timeweb VPS:** [`deploy/TIMEWEB.md`](deploy/TIMEWEB.md)

## Проверка

```bash
python scripts/check_infrastructure.py --public-url https://ваш-домен --skip-max
```

## Формат уведомления

```
Новый лид с сайта
Название: ...
Имя: ...
Телефон: ...
Город: ...
Вопросы по визе: ...
Карточка: https://портал.bitrix24.ru/crm/lead/details/ID/
```

Пустые поля не выводятся.
