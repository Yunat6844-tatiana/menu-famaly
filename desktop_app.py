#!/usr/bin/env python3
import html
import re
import tkinter as tk
import webbrowser
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

from bot import (
    DATA_PATH,
    TIMEZONE,
    day_response,
    format_help,
    format_pantry,
    format_shopping_list,
    format_week,
    load_json,
)


HTML_TAG_RE = re.compile(r"<[^>]+>")


def to_plain_text(value):
    return html.unescape(HTML_TAG_RE.sub("", value)).strip()


class ReadOnlyText(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.text = tk.Text(
            self,
            wrap="word",
            padx=16,
            pady=14,
            borderwidth=0,
            highlightthickness=0,
            font=("Arial", 14),
        )
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def set_text(self, value):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value)
        self.text.configure(state="disabled")


class MenuFamilyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Семейное меню")
        self.geometry("980x680")
        self.minsize(760, 540)

        self.menu = load_json(DATA_PATH, {})
        if not self.menu:
            messagebox.showerror("Нет данных", f"Не удалось прочитать меню: {DATA_PATH}")
            self.destroy()
            return

        self.configure(bg="#f5f1e8")
        self._configure_style()
        self._build_header()
        self._build_tabs()
        self.refresh_all()

    def _configure_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f1e8")
        style.configure("Header.TLabel", background="#f5f1e8", foreground="#1f2933", font=("Arial", 24, "bold"))
        style.configure("Subheader.TLabel", background="#f5f1e8", foreground="#5d6b76", font=("Arial", 12))
        style.configure("TButton", font=("Arial", 12), padding=(12, 8))
        style.configure("TNotebook", background="#f5f1e8", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Arial", 12), padding=(14, 9))

    def _build_header(self):
        header = ttk.Frame(self, padding=(18, 16, 18, 8))
        header.pack(fill="x")

        title = ttk.Label(header, text="Семейное меню", style="Header.TLabel")
        title.grid(row=0, column=0, sticky="w")

        now = datetime.now(TIMEZONE).strftime("%d.%m.%Y, %H:%M")
        subtitle = ttk.Label(
            header,
            text=f"Локальное приложение на данных Telegram-бота · Europe/Lisbon · {now}",
            style="Subheader.TLabel",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        refresh = ttk.Button(header, text="Обновить данные", command=self.refresh_all)
        refresh.grid(row=0, column=1, rowspan=2, sticky="e")
        header.columnconfigure(0, weight=1)

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.today_text = self._add_text_tab("Сегодня")
        self.tomorrow_text = self._add_text_tab("Завтра")
        self.week_text = self._add_text_tab("Неделя")
        self.shopping_text = self._add_text_tab("Покупки")
        self.pantry_text = self._add_text_tab("Дома")
        self._add_recipes_tab()
        self._add_chat_tab()

    def _add_text_tab(self, title):
        frame = ReadOnlyText(self.notebook)
        self.notebook.add(frame, text=title)
        return frame

    def _add_recipes_tab(self):
        frame = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(frame, text="Рецепты")

        info = ttk.Label(frame, text="Ссылки на рецепты и продукты из меню", style="Subheader.TLabel")
        info.pack(anchor="w", pady=(0, 10))

        canvas = tk.Canvas(frame, bg="#f5f1e8", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.recipes_container = ttk.Frame(canvas)
        self.recipes_container.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.recipes_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _add_chat_tab(self):
        frame = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(frame, text="Чат")

        self.chat_log = tk.Text(
            frame,
            wrap="word",
            height=18,
            padx=14,
            pady=12,
            borderwidth=0,
            highlightthickness=0,
            font=("Arial", 13),
        )
        self.chat_log.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.chat_log.configure(state="disabled")

        self.command_var = tk.StringVar(value="/today")
        command_entry = ttk.Entry(frame, textvariable=self.command_var, font=("Arial", 13))
        command_entry.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        command_entry.bind("<Return>", lambda event: self.send_chat_command())

        send = ttk.Button(frame, text="Отправить", command=self.send_chat_command)
        send.grid(row=1, column=1, padx=(10, 0), pady=(12, 0))

        help_button = ttk.Button(frame, text="/help", command=lambda: self.run_chat_command("/help"))
        help_button.grid(row=1, column=2, padx=(10, 0), pady=(12, 0))

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.run_chat_command("/help", show_user=False)

    def refresh_all(self):
        self.menu = load_json(DATA_PATH, {})
        today, _ = day_response(self.menu, datetime.now(TIMEZONE), "Меню на сегодня")
        tomorrow, _ = day_response(self.menu, datetime.now(TIMEZONE) + timedelta(days=1), "Меню на завтра")

        self.today_text.set_text(to_plain_text(today))
        self.tomorrow_text.set_text(to_plain_text(tomorrow))
        self.week_text.set_text(to_plain_text(format_week(self.menu)))
        self.shopping_text.set_text(to_plain_text(format_shopping_list(self.menu)))
        self.pantry_text.set_text(to_plain_text(format_pantry(self.menu)))
        self._refresh_recipes()

    def _refresh_recipes(self):
        for child in self.recipes_container.winfo_children():
            child.destroy()

        dish_links = self.menu.get("dish_links", {})
        row_index = 0
        for day_key, day in self.menu.get("week_menu", {}).items():
            day_title = day.get("title", day_key)
            day_label = ttk.Label(
                self.recipes_container,
                text=day_title,
                background="#f5f1e8",
                foreground="#1f2933",
                font=("Arial", 14, "bold"),
            )
            day_label.grid(row=row_index, column=0, sticky="w", pady=(10, 4))
            row_index += 1

            for meal_title, dish_name in (("Обед", day.get("lunch", "")), ("Ужин", day.get("dinner", ""))):
                meal = ttk.Label(
                    self.recipes_container,
                    text=f"{meal_title}: {dish_name}",
                    background="#f5f1e8",
                    foreground="#243746",
                    font=("Arial", 12),
                    wraplength=620,
                    justify="left",
                )
                meal.grid(row=row_index, column=0, sticky="w", padx=(10, 12), pady=3)

                links = dish_links.get(dish_name, {})
                recipe_url = links.get("recipe_url")
                ingredients_url = links.get("ingredients_url")
                if recipe_url:
                    ttk.Button(
                        self.recipes_container,
                        text="Рецепт",
                        command=lambda url=recipe_url: webbrowser.open(url),
                    ).grid(row=row_index, column=1, sticky="e", padx=4, pady=2)
                if ingredients_url:
                    ttk.Button(
                        self.recipes_container,
                        text="Продукты",
                        command=lambda url=ingredients_url: webbrowser.open(url),
                    ).grid(row=row_index, column=2, sticky="e", padx=4, pady=2)
                row_index += 1

        self.recipes_container.columnconfigure(0, weight=1)

    def send_chat_command(self):
        self.run_chat_command(self.command_var.get())
        self.command_var.set("")

    def run_chat_command(self, raw_command, show_user=True):
        command = raw_command.strip() or "/help"
        if show_user:
            self._append_chat(f"Вы: {command}\n")

        response = self.local_command_response(command)
        self._append_chat(f"Бот: {response}\n\n")

    def _append_chat(self, value):
        self.chat_log.configure(state="normal")
        self.chat_log.insert("end", value)
        self.chat_log.see("end")
        self.chat_log.configure(state="disabled")

    def local_command_response(self, raw_command):
        command = raw_command.strip().split()[0].lower()
        now = datetime.now(TIMEZONE)

        if command == "/start":
            text, _ = day_response(self.menu, now, "Меню на сегодня")
            return to_plain_text("Чатовый режим включен локально.\n\n" + text + "\n\n" + format_help())
        if command == "/today":
            text, _ = day_response(self.menu, now)
            return to_plain_text(text)
        if command == "/tomorrow":
            text, _ = day_response(self.menu, now + timedelta(days=1))
            return to_plain_text(text)
        if command == "/week":
            return to_plain_text(format_week(self.menu))
        if command == "/shopping":
            return to_plain_text(format_shopping_list(self.menu))
        if command == "/pantry":
            return to_plain_text(format_pantry(self.menu))
        if command == "/help":
            return to_plain_text(format_help())

        return to_plain_text("Не знаю такую команду.\n\n" + format_help())


def main():
    app = MenuFamilyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
