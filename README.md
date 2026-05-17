# Telegram menu bot

Бот отправляет меню на день, меню на неделю и общий список продуктов с ориентировочными ценами.

## Куда вставить токен

Откройте файл `.env` в этой папке:

`/Users/tarakanova/Documents/menu famaly/.env`

Внутри должна быть строка:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
DAILY_SEND_TIME=08:00
BOT_TIMEZONE=Europe/Lisbon
```

## Запуск

Если запускаете из Codex или терминала, используйте:

```bash
cd "/Users/tarakanova/Documents/menu famaly"
python3 bot.py
```

После запуска откройте бота в Telegram и отправьте `/start`.

## Приложение для компьютера

Локальное приложение использует те же данные меню и команды, но не требует Telegram-токен:

```bash
cd "/Users/tarakanova/Documents/menu famaly"
python3 desktop_app.py
```

На macOS можно также открыть файл `run_desktop_app.command` двойным кликом.

В приложении доступны вкладки с меню на сегодня, завтра, неделю, списком покупок, продуктами дома, ссылками на рецепты и локальным чатовым режимом команд `/today`, `/tomorrow`, `/week`, `/shopping`, `/pantry`, `/help`.

## Запуск через GitHub Actions

Workflow `.github/workflows/telegram-bot.yml` проверяет новые сообщения каждые 5 минут с 07:00 до 23:00 по `Europe/Lisbon`.
GitHub Actions не принимает Telegram webhook-запросы напрямую, поэтому бот работает в polling-режиме через Telegram `getUpdates`.

В GitHub откройте репозиторий и добавьте secret:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
Name: TELEGRAM_BOT_TOKEN
Value: токен от BotFather
```

После пуша workflow можно запустить вручную через `Actions -> Telegram bot -> Run workflow`, а дальше он будет работать по расписанию.

Файл `bot_state.json` хранит Telegram offset и сохраненные чаты. GitHub Actions обновляет и коммитит этот файл, чтобы не отвечать повторно на старые сообщения.

## Команды

- `/start` - сохранить чат для ежедневной рассылки;
- `/today` - меню на сегодня;
- `/tomorrow` - меню на завтра;
- `/week` - меню на неделю;
- `/shopping` - список продуктов с ценами;
- `/pantry` - продукты, которые уже есть дома;
- `/help` - помощь.

Файл с меню и списком покупок: `data/menu.json`.
