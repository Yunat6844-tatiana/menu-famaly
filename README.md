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

## Команды

- `/start` - сохранить чат для ежедневной рассылки;
- `/today` - меню на сегодня;
- `/tomorrow` - меню на завтра;
- `/week` - меню на неделю;
- `/shopping` - список продуктов с ценами;
- `/pantry` - продукты, которые уже есть дома;
- `/help` - помощь.

Файл с меню и списком покупок: `data/menu.json`.
