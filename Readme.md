# Руководство программиста

## 1. Условия развертывания

- Python 3.12+ или Docker
- Redis 7
- Google App Script;
- Переменные окружения в `.env`
- Установка зависимостей из `requirements.txt`

## 2. Характеристики программы

### Структура

| Структура | Назначение |
|----------------|------------|
| `main.py` | Запуск бота, подключение обработчиков, сохранение кэша при запуске |
| `handlers/` | Обработчики сообщений и нажатий кнопок |
| `services/` | Бизнес-логика и интеграция с telegram, гугл-таблицами и redis |
| `config/` | Конфигурация и интерфейс |
| `scheduler/` | Фоновые задачи (напоминания и проверка, не наступило ли время напоминания) |
| `gas/` | Код для Google App  Script |
| `tests/` | Тестирование |

### Модули

| Модуль | Назначение |
|--------|---------|
| `sheets_client.py` | Связь с Google App Script |
| `cache.py` | Кэширование |
| `bootstrap_cache.py` | Сохраняет в кэше при запуске список сотрудников, настроек, метаданых, названий листов расписания |
| `auth.py` | Проверка наличия доступа и роли по Telegram id |
| `payment.py` | Бизнес-логика подсчета оплаты |
| `telegram_session.py` | Подключение к Telegram |
| `shift_sort.py`, `sheet_names.py` | Сортировка смен и листов |

---

## 3. Запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```
Или

```bash
docker compose up -d --build
```

### Тестирование

```bash
pytest tests/ -v
```

### Настройка переменный в .env

| Переменная | Описание |
|------------|----------|
| BOT_TOKEN | Токен бота @firstcourse_work_bot |
| GAS_WEBAPP_URL | Ссылка развертывания из таблицы https://docs.google.com/spreadsheets/d/1-WRKGbNf0isIjp8DbAjnq79wCSvxmBXWYMu0P8ZHyMg/edit?gid=294501412#gid=294501412 |
| REDIS_URL | redis://localhost:6379/0 |
| ADMIN_TELEGRAM_ID | ID админа |
| PROXY_URL | SOCKS5 |


---

## 4. Входные и выходные данные

### Входные данные

| Место | Данные |
|----------|--------|
| Telegram | Cообщение, айди пользователя, вызовы функций |
| Google Таблица | Cетка расписания, сотрудники, настройки |
| `.env` | Токены, url |

### Выходные данные

| Место | Данные |
|------------|--------|
| Telegram | Текстовые сообщения, кнопки |
| Google Таблица | ФИ в ячейке, логи в журнале |
| Redis | Кэш JSON |

API Google App Script

**GET:** bootstrap, bookable_view, schedule_sheets, settings, employees, metadata, shifts_at_hour.

**POST:** book `{sheet, cell, name, tg_id}`, register_sheet `{sheet, opening_time}`.

Ответ: `{success: bool, reason?: string, cell?: string}`.

---

## 5. Сообщения

Необработанные исключения в `@dp.errors()`. Действия пользователей в листе "Журнал".

Ошибки из гугл-таблиц

| Имя | Значение |
|--------|----------|
| occupied | Ячейка занята |
| sheet_not_found | Лист не найден |
| lock_timeout | Не получена блокировка |

---

## 6. Добавление новых разделов

| Что добавлены | Файл в крле |
|--------|-------|
| Новая кнопка меню | `config/keyboards.py`, handler, `main.py` |
| Новая роль | Лист «Сотрудники», `@require_role`, keyboards |
| Новая логика в Google App Script | `Code.gs`, `sheets_client.py`, `gas_parse.py` |
| Изменение логики оплаты | `payment.py`, `test_payment.py` |

