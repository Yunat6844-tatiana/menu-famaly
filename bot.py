#!/usr/bin/env python3
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "menu.json"
STATE_PATH = BASE_DIR / "bot_state.json"
load_dotenv(BASE_DIR / ".env", override=True)
TIMEZONE = ZoneInfo(os.getenv("BOT_TIMEZONE", "Europe/Lisbon"))
DAILY_SEND_TIME = os.getenv("DAILY_SEND_TIME", "08:00")

WEEKDAY_KEYS = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday"
}

WEEKDAY_LABELS = {
    "monday": "Пн",
    "tuesday": "Вт",
    "wednesday": "Ср",
    "thursday": "Чт",
    "friday": "Пт",
    "saturday": "Сб",
    "sunday": "Вс"
}

COMMANDS = {
    "/start": "сохранить этот чат для ежедневной рассылки",
    "/today": "меню на сегодня",
    "/tomorrow": "меню на завтра",
    "/week": "меню на всю неделю",
    "/shopping": "общий список продуктов с ценами",
    "/pantry": "продукты, которые уже есть дома",
    "/help": "список команд"
}


def load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def api_request(token, method, params=None):
    params = params or {}
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(request, timeout=70) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {error.code} for {method}: {details}") from error
    result = json.loads(payload)
    if not result.get("ok"):
        raise RuntimeError(result)
    return result["result"]


def send_message(token, chat_id, text, reply_markup=None):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return api_request(token, "sendMessage", params)


def format_day(day):
    return (
        f"<b>{day['title']}</b>\n"
        f"Обед: {day['lunch']}\n"
        f"Ужин: {day['dinner']}"
    )


def format_week(menu):
    return "\n\n".join(format_day(day) for day in menu["week_menu"].values())


def dish_buttons(dish_name, dish_links, prefix):
    links = dish_links.get(dish_name, {})
    row = []
    if links.get("recipe_url"):
        row.append({"text": f"{prefix}: рецепт", "url": links["recipe_url"]})
    if links.get("ingredients_url"):
        row.append({"text": f"{prefix}: продукты", "url": links["ingredients_url"]})
    return [row] if row else []


def day_keyboard(menu, day):
    dish_links = menu.get("dish_links", {})
    keyboard = []
    keyboard.extend(dish_buttons(day["lunch"], dish_links, "Обед"))
    keyboard.extend(dish_buttons(day["dinner"], dish_links, "Ужин"))
    return {"inline_keyboard": keyboard} if keyboard else None


def week_keyboard(menu):
    dish_links = menu.get("dish_links", {})
    keyboard = []
    for day_key, day in menu["week_menu"].items():
        day_short = WEEKDAY_LABELS.get(day_key, day["title"][:2])
        keyboard.extend(dish_buttons(day["lunch"], dish_links, f"{day_short} обед"))
        keyboard.extend(dish_buttons(day["dinner"], dish_links, f"{day_short} ужин"))
    return {"inline_keyboard": keyboard} if keyboard else None


def format_shopping_list(menu):
    lines = ["<b>Список продуктов на неделю</b>"]
    total_low = 0.0
    total_high = 0.0

    for item in menu["shopping_list"]:
        price = item["estimated_price_eur"]
        low, high = parse_price_range(price)
        total_low += low
        total_high += high
        lines.append(f"- {item['name']}: {item['quantity']}, примерно {price} €")

    lines.append("")
    lines.append(f"<b>Итого ориентировочно:</b> {total_low:.0f}-{total_high:.0f} €")
    lines.append("Магазины: Pingo Doce, Mercadona, Auchan. Берите аналоги private label, если они дешевле.")
    return "\n".join(lines)


def parse_price_range(value):
    cleaned = value.replace(",", ".").replace("~", "")
    parts = cleaned.split("-")
    try:
        low = float(parts[0])
        high = float(parts[1]) if len(parts) > 1 else low
    except ValueError:
        return 0.0, 0.0
    return low, high


def format_pantry(menu):
    items = "\n".join(f"- {item}" for item in menu["pantry_items"])
    return f"<b>Уже есть дома</b>\n{items}"


def format_help():
    lines = ["<b>Команды</b>"]
    for command, description in COMMANDS.items():
        lines.append(f"{command} - {description}")
    lines.append("")
    lines.append(f"Ежедневная рассылка меню включена на {DAILY_SEND_TIME} по Europe/Lisbon после команды /start.")
    return "\n".join(lines)


def set_bot_commands(token):
    commands = [
        {"command": command.removeprefix("/"), "description": description}
        for command, description in COMMANDS.items()
    ]
    api_request(token, "setMyCommands", {"commands": json.dumps(commands, ensure_ascii=False)})


def day_message(menu, date):
    key = WEEKDAY_KEYS[date.weekday()]
    return format_day(menu["week_menu"][key])


def day_response(menu, date, prefix=None):
    key = WEEKDAY_KEYS[date.weekday()]
    day = menu["week_menu"][key]
    text = format_day(day)
    if prefix:
        text = prefix + "\n\n" + text
    return text, day_keyboard(menu, day)


def handle_command(token, chat_id, text, menu, state):
    command = text.strip().split()[0].lower()

    if command == "/start":
        chats = set(state.get("chat_ids", []))
        chats.add(str(chat_id))
        state["chat_ids"] = sorted(chats)
        state["last_daily_sent"] = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        save_json(STATE_PATH, state)
        today_text, keyboard = day_response(menu, datetime.now(TIMEZONE), "<b>Меню на сегодня</b>")
        return (
            "Чат сохранен. Теперь буду отправлять ежедневное меню.\n\n"
            + today_text
            + "\n\n"
            + format_help(),
            keyboard
        )
    if command == "/today":
        return day_response(menu, datetime.now(TIMEZONE))
    if command == "/tomorrow":
        return day_response(menu, datetime.now(TIMEZONE) + timedelta(days=1))
    if command == "/week":
        return format_week(menu), week_keyboard(menu)
    if command == "/shopping":
        return format_shopping_list(menu), None
    if command == "/pantry":
        return format_pantry(menu), None
    if command == "/help":
        return format_help(), None

    return "Не знаю такую команду.\n\n" + format_help(), None


def should_send_daily(state, now):
    last_sent = state.get("last_daily_sent")
    today_key = now.strftime("%Y-%m-%d")
    if last_sent == today_key:
        return False

    hour, minute = [int(part) for part in DAILY_SEND_TIME.split(":", 1)]
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return now >= scheduled


def send_daily_if_needed(token, menu, state):
    now = datetime.now(TIMEZONE)
    if not should_send_daily(state, now):
        return

    chat_ids = state.get("chat_ids", [])
    if not chat_ids:
        return

    text, keyboard = day_response(menu, now, "<b>Меню на сегодня</b>")
    for chat_id in chat_ids:
        try:
            send_message(token, chat_id, text, keyboard)
        except Exception as error:
            print(f"Daily send failed for chat {chat_id}: {error}", flush=True)

    state["last_daily_sent"] = now.strftime("%Y-%m-%d")
    save_json(STATE_PATH, state)


def run_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN before starting the bot.")

    menu = load_json(DATA_PATH, {})
    state = load_json(STATE_PATH, {"offset": 0, "chat_ids": []})
    set_bot_commands(token)

    while True:
        try:
            send_daily_if_needed(token, menu, state)
            updates = api_request(token, "getUpdates", {
                "offset": state.get("offset", 0),
                "timeout": 25,
                "allowed_updates": json.dumps(["message"])
            })

            for update in updates:
                state["offset"] = update["update_id"] + 1
                message = update.get("message") or {}
                chat = message.get("chat") or {}
                text = message.get("text", "")
                chat_id = chat.get("id")

                if not chat_id or not text.startswith("/"):
                    continue

                response, keyboard = handle_command(token, chat_id, text, menu, state)
                send_message(token, chat_id, response, keyboard)

            save_json(STATE_PATH, state)
        except (urllib.error.URLError, TimeoutError) as error:
            print(f"Network error: {error}. Retrying in 10 seconds.", flush=True)
            time.sleep(10)
        except Exception as error:
            print(f"Bot error: {error}. Retrying in 10 seconds.", flush=True)
            time.sleep(10)


if __name__ == "__main__":
    run_bot()
