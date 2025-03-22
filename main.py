import asyncio
import json
import os
import sys
import requests
from telethon import events, TelegramClient, Button
from telethon.tl.functions.account import UpdateProfileRequest
import pytz
from datetime import datetime
import random
from itertools import cycle

# Константы
CONFIG_FILE = "config.json"
DEFAULT_TYPING_SPEED = 0.3
DEFAULT_CURSOR = "\u2588"  # Символ по умолчанию для анимации
SCRIPT_VERSION = "1.4.32"

# Глобальная переменная для хранения задачи обновления имени
update_name_task = None

# Глобальные переменные для игр
tictactoe_games = {}  # Словарь для хранения состояний игр в крестики-нолики

async def update_profile_name(client):
    """Функция для обновления имени аккаунта в зависимости от московского времени."""
    global update_name_task
    moscow_tz = pytz.timezone('Europe/Moscow')
    
    while True:
        now = datetime.now(moscow_tz)
        time_str = now.strftime("%H:%M")  # Только время в формате HH:MM
        
        try:
            await client(UpdateProfileRequest(
                first_name=time_str  # Устанавливаем только время
            ))
        except Exception as e:
            print(f"Ошибка при обновлении имени: {e}")
        
        await asyncio.sleep(60)  # Обновляем каждую минуту

async def main(chat_id):
    global update_name_task

    # Проверяем наличие файла конфигурации
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            user_config = config.get(str(chat_id))
            if not user_config:
                print(f"Конфигурация для пользователя {chat_id} не найдена.")
                return

            API_ID = user_config.get("API_ID")
            API_HASH = user_config.get("API_HASH")
            PHONE_NUMBER = user_config.get("PHONE_NUMBER")
            typing_speed = user_config.get("typing_speed", DEFAULT_TYPING_SPEED)
            cursor_symbol = user_config.get("cursor_symbol", DEFAULT_CURSOR)

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Ошибка чтения конфигурации: {e}. Удалите {CONFIG_FILE} и попробуйте снова.")
            return
    else:
        print("Конфигурация не найдена. Запустите бота и настройте его через Telegram.")
        return

    # Уникальное имя файла для сессии
    SESSION_FILE = f'session_{PHONE_NUMBER.replace("+", "").replace("-", "")}'

    # Инициализация клиента
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

    @client.on(events.NewMessage(pattern=r'/p (.+)'))
    async def animated_typing(event):
        """Команда для печатания текста с анимацией."""
        try:
            if not event.out:
                return

            # Получаем конфигурацию пользователя
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            user_config = config.get(str(chat_id))
            if not user_config:
                await event.reply("<b>Конфигурация для пользователя не найдена.</b>", parse_mode='html')
                return

            typing_speed = user_config.get("typing_speed", DEFAULT_TYPING_SPEED)
            cursor_symbol = user_config.get("cursor_symbol", DEFAULT_CURSOR)

            text = event.pattern_match.group(1)
            typed_text = ""

            for char in text:
                typed_text += char
                await event.edit(typed_text + cursor_symbol)
                await asyncio.sleep(typing_speed)

            await event.edit(typed_text)
        except Exception as e:
            print(f"Ошибка анимации: {e}")
            await event.reply("<b>Произошла ошибка во время выполнения команды.</b>", parse_mode='html')

    @client.on(events.NewMessage(pattern=r'/s (\d*\.?\d+)'))
    async def set_typing_speed(event):
        """Команда для изменения скорости печатания."""
        try:
            if not event.out:
                return

            new_speed = float(event.pattern_match.group(1))

            if 0.1 <= new_speed <= 0.5:
                # Загружаем конфигурацию пользователя
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                config[str(chat_id)]["typing_speed"] = new_speed

                # Сохраняем обновленную конфигурацию
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f)

                await event.reply(f"<b>Скорость печатания изменена на {new_speed} секунд.</b>", parse_mode='html')
            else:
                await event.reply("<b>Введите значение задержки в диапазоне от 0.1 до 0.5 секунд.</b>", parse_mode='html')

        except ValueError:
            await event.reply("<b>Некорректное значение. Укажите число в формате 0.1 - 0.5.</b>", parse_mode='html')
        except Exception as e:
            print(f"Ошибка при изменении скорости: {e}")
            await event.reply("<b>Произошла ошибка при изменении скорости.</b>", parse_mode='html')

    @client.on(events.NewMessage(pattern=r'/c (.+)'))
    async def change_cursor(event):
        """Команда для изменения символа курсора анимации."""
        try:
            if not event.out:
                return

            new_cursor = event.pattern_match.group(1).strip()

            if new_cursor:
                # Загружаем конфигурацию пользователя
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                config[str(chat_id)]["cursor_symbol"] = new_cursor

                # Сохраняем обновленную конфигурацию
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f)

                await event.reply(f"<b>Символ курсора изменен на: {new_cursor}</b>", parse_mode='html')
            else:
                await event.reply("<b>Введите корректный символ для курсора.</b>", parse_mode='html')
        except Exception as e:
            print(f"Ошибка при изменении символа: {e}")
            await event.reply("<b>Произошла ошибка при изменении символа курсора.</b>", parse_mode='html')

    @client.on(events.NewMessage(pattern=r'/sp (.+) (\d+) (\d*\.?\d+)'))
    async def spam_message(event):
        """Команда для спама сообщений."""
        try:
            if not event.out:
                return

            message = event.pattern_match.group(1)
            count = int(event.pattern_match.group(2))
            speed = float(event.pattern_match.group(3))

            if count <= 0 or speed <= 0:
                await event.reply("<b>Количество сообщений и скорость должны быть положительными числами.</b>", parse_mode='html')
                return

            for _ in range(count):
                await event.reply(message)
                await asyncio.sleep(speed)

        except Exception as e:
            print(f"Ошибка при спаме: {e}")
            await event.reply("<b>Произошла ошибка при отправке сообщений.</b>", parse_mode='html')

    @client.on(events.NewMessage(pattern="Сердце"))
    async def heart_figure(event):
        """Фигурка сердца."""
        heart_figure = """⣿⣿⣿⡿⠟⠛⠛⠛⠛⠿⣿⣿⣿⣿⡿⠟⠛⠛⠛⠛⠻⣿⣿⣿⣿
⣿⡿⠉⠰⠾⠿⢋⣠⣄⠀⡈⠻⡿⠋⣀⢀⣤⣬⢛⣡⣄⢀⠙⢿⣿
⡏⢀⢠⣾⣿⣶⣿⣿⣿⡇⠿⠆⢀⣾⠿⠘⣿⣿⣿⣿⡿⣸⣧⠈⣿
⠁⣸⡈⠿⣿⣿⣿⣿⠟⡀⣴⣷⣦⣡⣶⣦⡈⠻⠟⠋⣐⠻⣿⠀⢸
⡄⢸⣿⣶⣌⠙⠻⠋⣼⣧⠻⣿⣿⣿⣿⡿⣱⢓⣨⣸⣿⡇⣿⠀⢸
⣇⠈⡟⣉⣴⡷⠁⣠⣌⠻⡷⢌⠻⠟⠁⠶⣿⡘⠿⠿⠿⠇⠟⢀⣿
⣿⣦⠀⢹⣛⣃⠸⣿⣿⣧⣶⣦⠠⡆⣾⣿⣮⣤⣤⠐⣶⠆⢀⣿⣿
⣿⣿⣷⡄⠙⢿⣆⢻⣿⣿⡿⠏⠘⠃⠙⣿⣿⣿⠟⠀⠁⣰⣿⣿⣿
⣿⣿⣿⣿⣷⣄⠙⠂⡥⢀⣤⣠⣿⣿⠀⡌⣋⠄⢀⣴⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣷⣤⡀⠘⠿⣿⣿⠏⣼⠟⢁⣴⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⠐⢶⣬⠀⢁⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡄⠁⣰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿"""

        await event.edit(heart_figure)  # Отправляем фигурку сердца

    @client.on(events.NewMessage(pattern='/rundate'))
    async def start_update_name(event):
        """Команда для запуска обновления имени аккаунта."""
        global update_name_task

        if update_name_task is not None and not update_name_task.done():
            await event.reply("<b>Обновление имени уже запущено.</b>", parse_mode='html')
            return

        update_name_task = asyncio.create_task(update_profile_name(client))
        await event.reply("<b>Обновление имени аккаунта запущено.</b>", parse_mode='html')

    @client.on(events.NewMessage(pattern='/stopdate'))
    async def stop_update_name(event):
        """Команда для остановки обновления имени аккаунта."""
        global update_name_task

        if update_name_task is None or update_name_task.done():
            await event.reply("<b>Обновление имени не запущено.</b>", parse_mode='html')
            return

        update_name_task.cancel()
        update_name_task = None
        await event.reply("<b>Обновление имени аккаунта остановлено.</b>", parse_mode='html')


    @client.on(events.NewMessage(pattern="Привет!"))
    async def hello_figure(event):
        """Фигурка HELLO."""
        hello_figure = """┈┈┈┈┈┈ⒽⒺⓁⓁⓄ┈┈┈┈┈
╭━━╮┈┈┈╭━━╮┈┈┈┈┈
┃╭╮┣━━━┫╭╮┃┈╭┳┳╮
╰━┳╯▆┈▆╰┳━╯┈┃┃┃┃
┈┈┃┓┈◯┈┏┃┈┈╭┫┗┗┃
┈┈┃╰┳┳┳╯┃┈┈┃┃╭━┃
╭━┻╮┗┻┛╭┻━╮╰┳━┳╯
┃┈┈╰━━━╯┈┈╰━┛┈┃┈"""

        await event.edit(hello_figure)  # Отправляем фигурку привет!

    @client.on(events.NewMessage(pattern="Блесс"))
    async def bless_figure(event):
        """Фигурка Bless."""
        bless_figure = """⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⡿⢿⣿⣿⣿⠀⣿⣿⣿⡿⠻⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣷⡈⠻⣿⣿⠀⣿⣿⡟⢁⣾⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⡿⠏⠀⠙⣿⣿⣦⣿⣿⣿⣿⣿⣤⣿⣿⠋⠀⠹⢿⣿⣿⣿
⣿⡿⠇⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠸⢿⣿
⣿⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⣿
⣿⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⣿
⣿⠀⠀⠀⠀⠀⠀⠀⠸⠛⠉⠉⠿⠉⠉⠛⠇⠀⠀⠀⠀⠀⠀⠀⣿
⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣴⣿⣦⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹
⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿
⣿⣧⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⣼⣿
⣿⣿⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⣿⣿
⣿⣿⣀⣀⣀⣀⣀⣀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣀⣀⣀⣀⣀⣀⣿⣿"""

        await event.edit(bless_figure)  # Отправляем фигурку Bless

    @client.on(events.NewMessage(pattern='/chiks'))
    async def draw_chiks(event):
        """Анимация фигурки 'Чикс'."""
    chiks_figure = [
        "⣿⣿⣿⣿⣿⣿⣿⠋⣉⡙⠛⣉⣉⠻⣿⣿⣿⣿⣿⣿",
        "⣿⣿⣿⣿⣿⣿⣿⠸⣿⣿⣾⣿⡿⠀⣿⣿⣿⣿⣿⣿",
        "⣿⣿⣿⣿⣿⣿⣿⣦⡘⠻⣿⠟⣡⣾⣿⣿⣿⣿⣿⣿",
        "⣿⣿⣿⣿⣿⣿⠿⢿⣿⣶⣤⣼⠟⠻⢿⣿⣿⣿⣿⣿",
        "⣿⣿⣿⣿⣿⢡⣶⣦⡌⠻⡿⢁⣾⣷⠀⣿⣿⣿⣿⣿",
        "⣿⣿⣿⣿⣿⡄⢻⣿⣿⣦⡀⢸⣿⡏⣸⣿⣿⣿⣿⣿",
        "⣿⣿⣿⣿⣿⣿⣦⠙⢿⣿⣿⣆⠙⢠⣿⣿⣿⣿⣿⣿",
        "⣿⣿⣿⣿⣿⣿⣿⣷⡌⠻⣿⣿⣷⣄⠻⣿⣿⣿⣿⣿",
        "⣿⣿⣿⣿⣿⣿⣿⢡⣴⣤⡘⢿⣿⣿⣧⡈⢿⣿⣿⣿",
        "⣿⣿⣿⣿⡟⢋⣁⠘⢿⣿⣿⣆⠙⣿⣿⣷⡀⢻⣿⣿",
        "⣿⣿⣿⠿⠀⣿⣿⣷⣄⠻⣿⣿⣿⣿⣿⣿⣷⠈⣿⣿",
        "⣿⡟⢠⣶⣤⡈⠻⣿⣿⣷⣿⣿⣿⣿⣿⣿⠏⣰⣿⣿",
        "⣿⣿⡈⢿⣿⣿⣶⣼⣿⣿⣿⣿⣿⣿⣿⠋⣰⣿⣿⣿",
        "⣿⣿⣷⣄⠙⢿⣿⣿⣿⣿⣿⣿⡿⠟⣡⣾⣿⣿⣿⣿",
        "⣿⣿⣿⣿⣷⣦⣉⠛⠛⠛⢛⣉⣴⣾⣿⣿⣿⣿⣿⣿"
    ]


    # Постепенно добавляем строки с задержкой
    for line in chiks_figure:
        await asyncio.sleep(0.5)  # Задержка между строками

    @client.on(events.NewMessage(pattern="Скучаю"))
    async def imissyou_figure(event):
        """Фигурка Скучаю."""
        imissyou_figure = """
╔══╗───╔╦═╦═╗
╚║║╝╔══╬╣═╣═╣╔╦╦═╦╦╗
╔║║╗║║║║╠═╠═║║║║╬║║║
╚══╝╚╩╩╩╩═╩═╝╠╗╠═╩═╝
.💝🌷💝🌷💝🌷💝🌷💝"""

        await event.edit(imissyou_figure)  # Отправляем фигурку скучаю

    @client.on(events.NewMessage(pattern='/cat'))
    async def send_cat(event):
        try:
            response = requests.get("https://api.thecatapi.com/v1/images/search").json()
            cat_url = response[0]["url"]
            await client.send_file(event.chat_id, cat_url)
        except Exception as e:
            await event.reply(f"Не удалось получить котика. Ошибка: {e}")


    @client.on(events.NewMessage(pattern="Тянка"))
    async def tyanka_figure(event):
        """Фигурка Тянка."""
        tyanka_figure = """⠄⠄⡇⠄⡾⡀⠄⠄⠄⠄⣀⣹⣆⡀⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⢹
⠄⢸⠃⢀⣇⡈⠄⠄⠄⠄⠄⠄⢀⡑⢄⡀⢀⡀⠄⠄⠄⠄⠄⠄⢸
⠄⢸⠄⢻⡟⡻⢶⡆⠄⠄⠄⠄⡼⠟⡳⢿⣦⡑⢄⠄⠄⠄⠄⠄⢸
⠄⣸⠄⢸⠃⡇⢀⠇⠄⠄⠄⠄⠄⡼⠄⠄⠈⣿⡗⠂⠄⠄⠄⠄⢸
⠄⡏⠄⣼⠄⢳⠊⠄⠄⠄⠄⠄⠄⠱⣀⣀⠔⣸⠁⠄⠄⠄⠄⢠⡟
⠄⡇⢀⡇⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠠⠄⡇⠄⠄⠄⠄⠄⠄⢸⠃
⢸⠃⠘⡇⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⢸⠁⠄⠄⢀⠄⠄⣾
⣸⠄⠄⠹⡄⠄⠄⠈⠁⠄⠄⠄⠄⠄⠄⠄⡞⠄⠄⠄⠸⠄⠄⡇
⡏⠄⠄⠄⠙⣆⠄⠄⠄⠄⠄⠄⠄⢀⣠⢶⡇⠄⠄⢰⡀⠄⠄⡇
⠇⡄⠄⠄⠄⡿⢣⣀⣀⣀⡤⠴⡞⠉⠄⢸⠄⠄⠄⣿⡇⠄⠄⣧
⠄⡇⠄⠄⠄⠄⠄⠄⠉⠄⠄⠄⢹⠄⠄⢸⠄⠄⢀⣿⠇⠄⠁⢸
⠄⡇⠄⠄⠄⠄⠄⢀⡤⠤⠶⠶⠾⠤⠄⢸⠄⡀⠸⣿⣀⠄⠄⠈⣇"""

        await event.edit(tyanka_figure)  # Отправляем фигурку Тянка

    @client.on(events.NewMessage(pattern="Мы"))
    async def etomi_figure(event):
        """Фигурка Мы."""
        etomi_figure = """┳┻┳┻╭━━━━╮╱▔▔▔╲
┻┳┻┳┃╯╯╭━┫▏╰╰╰▕
┳┻┳┻┃╯╯┃▔╰┓▔▂▔▕╮
┻┳┻┳╰╮╯┃┈╰┫╰━╯┏╯
┳┻┳┻┏╯╯┃╭━╯┳━┳╯
┻┳┻┳╰━┳╯▔╲╱▔╭╮▔╲
┳┻┳┻┳┻┃┈╲┈╲╱╭╯╮▕
┻┳┻┳┻┳┃┈▕╲▂╱┈╭╯"""

        await event.edit(etomi_figure)  # Отправляем фигурку Мы

    @client.on(events.NewMessage(pattern="Целую"))
    async def celuyu(event):
        """Фигурка с сердечками разных цветов."""
        celuyu_figure = [
            """
💨💨💨💨💨💨💨💨
💨💨❤️🧡💨❤️🧡💨
💨💨❤️🧡💛💚💨💨
💨💨❤️🧡💛💨💨💨
💨💨❤️🧡💛💚💨💨
💨💨❤️🧡💨❤️🧡💨
💨💨💨💨💨💨💨💨
            """,
            """
💨💨💨💨💨💨💨💨
💨💨❤️🧡💛💚💨💨
💨💨💨❤️🧡💨💨💨
💨💨💨❤️🧡💨💨💨
💨💨💨❤️🧡💨💨💨
💨💨❤️🧡💛💚💨💨
💨💨💨💨💨💨💨💨
            """,
            """
💨💨💨💨💨💨💨💨
💨💨💨❤️🧡💛💨💨
💨💨❤️🧡💨💨💨💨
💨💨❤️🧡💛💚💨💨
💨💨💨💨❤️🧡💨💨
💨💨❤️🧡💛💨💨💨
💨💨💨💨💨💨💨💨
            """,
            """
💨💨💨💨💨💨💨💨
💨💨💨❤️🧡💛💨💨
💨💨❤️🧡💨💨💨💨
💨💨❤️🧡💛💚💨💨
💨💨💨💨❤️🧡💨💨
💨💨❤️🧡💛💨💨💨
💨💨💨💨💨💨💨💨
💨💨💨💨💨💨💨💨
            """
        ]

        for celuyu in celuyu_figure:
            await event.edit(celuyu)  # Обновление текущего сообщения
            await asyncio.sleep(1.1)  # Задержка в 1.1 секунды между кадрами

    @client.on(events.NewMessage(pattern="сердечки"))
    async def heart(event):
     # Начальное сообщение
        stages = [
        "🤍", "🤍🤍", "🤍🤍🤍", "🤍🤍🤍🤍", "🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍", "🤍🤍🤍🤍🤍🤍🤍", "🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️❤️🤍❤️❤️🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️❤️🤍❤️❤️🤍🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️❤️🤍❤️❤️🤍🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️❤️🤍❤️❤️🤍🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍🤍❤️❤️❤️❤️❤️🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️❤️🤍❤️❤️🤍🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍🤍❤️❤️❤️❤️❤️🤍🤍\n🤍🤍🤍❤️❤️❤️🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️❤️🤍❤️❤️🤍🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍🤍❤️❤️❤️❤️❤️🤍🤍\n🤍🤍🤍❤️❤️❤️🤍🤍🤍\n🤍🤍🤍🤍❤️🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍💗💗🤍💗💗🤍🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍🤍❤️❤️❤️❤️❤️🤍🤍\n🤍🤍🤍❤️❤️❤️🤍🤍🤍\n🤍🤍🤍🤍❤️🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍💗💗🤍💗💗🤍🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍❤️❤️❤️❤️❤️❤️❤️🤍\n🤍🤍❤️❤️❤️❤️❤️🤍🤍\n🤍🤍🤍❤️❤️❤️🤍🤍🤍\n🤍🤍🤍🤍❤️🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍💗💗🤍💗💗🤍🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍🤍❤️❤️❤️❤️❤️🤍🤍\n🤍🤍🤍❤️❤️❤️🤍🤍🤍\n🤍🤍🤍🤍❤️🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍💗💗🤍💗💗🤍🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍❤️❤️❤️🤍🤍🤍\n🤍🤍🤍🤍❤️🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍💗💗🤍💗💗🤍🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍❤️🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍💗💗🤍💗💗🤍🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️‍🩹❤️‍🩹🤍❤️‍🩹❤️‍🩹🤍🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️‍🩹❤️‍🩹🤍❤️‍🩹❤️‍🩹🤍🤍\n🤍❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️‍🩹❤️‍🩹🤍❤️‍🩹❤️‍🩹🤍🤍\n🤍❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹🤍\n🤍❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹🤍\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️‍🩹❤️‍🩹🤍❤️‍🩹❤️‍🩹🤍🤍\n🤍❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹🤍\n🤍❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹🤍\n🤍🤍❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹🤍🤍\n🤍🤍🤍❤️‍🩹❤️‍🩹❤️‍🩹🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🤍🤍🤍🤍🤍🤍🤍🤍🤍\n🤍🤍❤️‍🩹❤️‍🩹🤍❤️‍🩹❤️‍🩹🤍🤍\n🤍❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹🤍\n🤍❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹🤍\n🤍🤍❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹❤️‍🩹🤍🤍\n🤍🤍🤍❤️‍🩹❤️‍🩹❤️‍🩹🤍🤍🤍\n🤍🤍🤍🤍❤️‍🩹🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🍀🍀🍀🍀🍀🍀🍀🍀🍀\n🤍🤍💗💗🤍💗💗🤍🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🍀🍀🍀🍀🍀🍀🍀🍀🍀\n🍀🍀💖💖🍀💖💖🍀🍀\n🤍💗💗💗💗💗💗💗🤍\n🤍💗💗💗💗💗💗💗🤍\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍", 
        "🍀🍀🍀🍀🍀🍀🍀🍀🍀\n🍀🍀💖💖🍀💖💖🍀🍀\n🍀💖💖💖💖💖💖💖🍀\n🤍💗💗💗💗💗💗💗🤍\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",  
        "🍀🍀🍀🍀🍀🍀🍀🍀🍀\n🍀🍀💖💖🍀💖💖🍀🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀💖💖💖💖💖💖💖🍀\n🤍🤍💗💗💗💗💗🤍🤍\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🍀🍀🍀🍀🍀🍀🍀🍀🍀\n🍀🍀💖💖🍀💖💖🍀🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀🍀💖💖💖💖💖🍀🍀\n🤍🤍🤍💗💗💗🤍🤍🤍\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",  
        "🍀🍀🍀🍀🍀🍀🍀🍀🍀\n🍀🍀💖💖🍀💖💖🍀🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀🍀💖💖💖💖💖🍀🍀\n🍀🍀🍀💖💖💖🍀🍀🍀\n🤍🤍🤍🤍💗🤍🤍🤍🤍\n🤍🤍🤍🤍🤍🤍🤍🤍🤍",
        "🍀🍀🍀🍀🍀🍀🍀🍀🍀\n🍀🍀💖💖🍀💖💖🍀🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀🍀💖💖💖💖💖🍀🍀\n🍀🍀🍀💖💖💖🍀🍀🍀\n🍀🍀🍀🍀💖🍀🍀🍀🍀\n🤍🤍🤍🤍🤍🤍🤍🤍🤍", 
        "🍀🍀🍀🍀🍀🍀🍀🍀🍀\n🍀🍀💖💖🍀💖💖🍀🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀🍀💖💖💖💖💖🍀🍀\n🍀🍀🍀💖💖💖🍀🍀🍀\n🍀🍀🍀🍀💖🍀🍀🍀🍀\n🍀🍀🍀🍀🍀🍀🍀🍀🍀", 
        "🌴🌴🌴🌴🌴🌴🌴🌴🌴\n🍀🍀💖💖🍀💖💖🍀🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀🍀💖💖💖💖💖🍀🍀\n🍀🍀🍀💖💖💖🍀🍀🍀\n🍀🍀🍀🍀💖🍀🍀🍀🍀\n🍀🍀🍀🍀🍀🍀🍀🍀🍀",  
        "🌴🌴🌴🌴🌴🌴🌴🌴🌴\n🌴🌴🐼🐼🌴🐼🐼🌴🌴\n🍀💖💖💖💖💖💖💖🍀\n🍀💖💖💖💖💖💖💖🍀\n🍀🍀💖💖💖💖💖🍀🍀\n🍀🍀🍀💖💖💖🍀🍀🍀\n🍀🍀🍀🍀💖🍀🍀🍀🍀\n🍀🍀🍀🍀🍀🍀🍀🍀🍀", 
        "🌴🌴🌴🌴🌴🌴🌴🌴🌴\n🌴🌴🐼🐼🌴🐼🐼🌴🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🍀💖💖💖💖💖💖💖🍀\n🍀🍀💖💖💖💖💖🍀🍀\n🍀🍀🍀💖💖💖🍀🍀🍀\n🍀🍀🍀🍀💖🍀🍀🍀🍀\n🍀🍀🍀🍀🍀🍀🍀🍀🍀",  
        "🌴🌴🌴🌴🌴🌴🌴🌴🌴\n🌴🌴🐼🐼🌴🐼🐼🌴🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🍀🍀💖💖💖💖💖🍀🍀\n🍀🍀🍀💖💖💖🍀🍀🍀\n🍀🍀🍀🍀💖🍀🍀🍀🍀\n🍀🍀🍀🍀🍀🍀🍀🍀🍀",  
        "🌴🌴🌴🌴🌴🌴🌴🌴🌴\n🌴🌴🐼🐼🌴🐼🐼🌴🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🌴🐼🐼🐼🐼🐼🌴🌴\n🍀🍀🍀💖💖💖🍀🍀🍀\n🍀🍀🍀🍀💖🍀🍀🍀🍀\n🍀🍀🍀🍀🍀🍀🍀🍀🍀",  
        "🌴🌴🌴🌴🌴🌴🌴🌴🌴\n🌴🌴🐼🐼🌴🐼🐼🌴🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🌴🐼🐼🐼🐼🐼🌴🌴\n🌴🌴🌴🐼🐼🐼🌴🌴🌴\n🍀🍀🍀🍀💖🍀🍀🍀🍀\n🍀🍀🍀🍀🍀🍀🍀🍀🍀",  
        "🌴🌴🌴🌴🌴🌴🌴🌴🌴\n🌴🌴🐼🐼🌴🐼🐼🌴🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🌴🐼🐼🐼🐼🐼🌴🌴\n🌴🌴🌴🐼🐼🐼🌴🌴🌴\n🌴🌴🌴🌴🐼🌴🌴🌴🌴\n🍀🍀🍀🍀🍀🍀🍀🍀🍀", 
        "🌴🌴🌴🌴🌴🌴🌴🌴🌴\n🌴🌴🐼🐼🌴🐼🐼🌴🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🌴🐼🐼🐼🐼🐼🌴🌴\n🌴🌴🌴🐼🐼🐼🌴🌴🌴\n🌴🌴🌴🌴🐼🌴🌴🌴🌴\n🌴🌴🌴🌴🌴🌴🌴🌴🌴",
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n🌴🌴🐼🐼🌴🐼🐼🌴🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🌴🌴🐼🐼🐼🌴🌴🌴\n🌴🌴🌴🌴🐼🌴🌴🌴🌴\n🌴🌴🌴🌴🌴🌴🌴🌴🌴",
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️💟💟☁️💟💟☁️☁️\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🌴🌴🐼🐼🐼🌴🌴🌴\n🌴🌴🌴🌴🐼🌴🌴🌴🌴\n🌴🌴🌴🌴🌴🌴🌴🌴🌴", 
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️💟💟☁️💟💟☁️☁️\n☁️💟💟💟💟💟💟💟☁️\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🌴🌴🐼🐼🐼🌴🌴🌴\n🌴🌴🌴🌴🐼🌴🌴🌴🌴\n🌴🌴🌴🌴🌴🌴🌴🌴🌴",  
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️💟💟☁️💟💟☁️☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️💟💟💟💟💟💟💟☁️\n🌴🐼🐼🐼🐼🐼🐼🐼🌴\n🌴🌴🌴🐼🐼🐼🌴🌴🌴\n🌴🌴🌴🌴🐼🌴🌴🌴🌴\n🌴🌴🌴🌴🌴🌴🌴🌴🌴",   
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️💟💟☁️💟💟☁️☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️☁️💟💟💟💟💟☁️☁️\n🌴🌴🌴🐼🐼🐼🌴🌴🌴\n🌴🌴🌴🌴🐼🌴🌴🌴🌴\n🌴🌴🌴🌴🌴🌴🌴🌴🌴",  
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️💟💟☁️💟💟☁️☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️☁️💟💟💟💟💟☁️☁️\n☁️☁️☁️💟💟💟☁️☁️☁️\n🌴🌴🌴🌴🐼🌴🌴🌴🌴\n🌴🌴🌴🌴🌴🌴🌴🌴🌴",   
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️💟💟☁️💟💟☁️☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️☁️💟💟💟💟💟☁️☁️\n☁️☁️☁️💟💟💟☁️☁️☁️\n☁️☁️☁️☁️💟☁️☁️☁️☁️\n🌴🌴🌴🌴🌴🌴🌴🌴🌴",   
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️💟💟☁️💟💟☁️☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️☁️💟💟💟💟💟☁️☁️\n☁️☁️☁️💟💟💟☁️☁️☁️\n☁️☁️☁️☁️💟☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",  
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️☁️💟💟💟💟💟☁️☁️\n☁️☁️☁️💟💟💟☁️☁️☁️\n☁️☁️☁️☁️💟☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",  
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️💟💟💟💟💟💟💟☁️\n☁️☁️💟💟💟💟💟☁️☁️\n☁️☁️☁️💟💟💟☁️☁️☁️\n☁️☁️☁️☁️💟☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",  
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️💟💟💟💟💟☁️☁️\n☁️☁️☁️💟💟💟☁️☁️☁️\n☁️☁️☁️☁️💟☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",  
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️💟💟💟☁️☁️☁️\n☁️☁️☁️☁️💟☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️", 
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️💟☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️", 
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",   
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️\n☁️☁️☁️☁️☁️☁️☁️☁️☁️",
        "☁️☁️☁️☁️☁️☁️☁️☁️☁️",
        "❤️❤️i☁️☁️☁️☁️☁️☁️☁️☁️",
        "❤️❤️i❤️❤️love☁️☁️☁️☁️☁️☁️", 
        "❤️❤️i❤️❤️love❤️❤️you☁️☁️☁️☁️",   
        "❤️❤️i❤️❤️love❤️❤️you❤️❤️forever☁️☁️",  
        "❤️❤️i❤️❤️love❤️❤️you❤️❤️forever❤️❤️",







        # 
    ]

        for stage in stages:
            await event.edit(stage)  # Обновление текущего сообщения
        await asyncio.sleep(0.3)  # Задержка в 0.3 секунды между кадрами

    await client.start(phone=PHONE_NUMBER)
    await client.run_until_disconnected()

if __name__ == "__main__":
    chat_id = sys.argv[1] if len(sys.argv) > 1 else None
    if chat_id:
        asyncio.run(main(chat_id))
    else:
        print("Не указан chat_id.")
