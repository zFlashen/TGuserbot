import telebot
from telebot import types
import json
import os
import asyncio

# Константы
CONFIG_FILE = "config.json"
DEFAULT_TYPING_SPEED = 0.3
DEFAULT_CURSOR = "\u2588"  # Символ по умолчанию для анимации

# Инициализация бота
bot = telebot.TeleBot('8141257649:AAF_tH89AM2AY2rALOGGfTwsMCgZrsj1fQo')

# Состояния для ввода данных
user_data = {}

# Меню
menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
poluchit = types.KeyboardButton('Запустить бота✅')
comandi = types.KeyboardButton('Команды бота⚙️')
menu.add(poluchit, comandi)

back = types.ReplyKeyboardMarkup(resize_keyboard=True)
back_button = types.KeyboardButton("Назад")
back.add(back_button)

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Вас приветствует юзербот!", reply_markup=menu)

@bot.message_handler(content_types=['text'])
def text_messages(message):
    if message.text == "Назад":
        bot.send_message(message.chat.id, "Для подключения функции нажмите на (Запустить бота).", reply_markup=menu)
    elif message.text == "Команды бота⚙️":
        commands_text = (
            "Напишите в чате /p (текст) для анимации печатания.\n"
            "- Используйте /s (задержка) для изменения скорости печатания.\n"
            "- Используйте /c (символ) для изменения символа курсора анимации.\n"
            "= Используйте /sp (текст) (количество) (скорость отправки).\n"
            "- Используйте /support для поддержки автора.\n"
            "- Используйте /update для проверки обновления.\n"
            "- Используйте слово (сердечки) для создания анимации сердца."
        )
        bot.send_message(message.chat.id, commands_text, reply_markup=back)
    elif message.text == "Вернуться":
        bot.send_message(message.chat.id, "Нажмите кнопку 'назад' чтобы выйти в главное меню.", reply_markup=back)
    elif message.text == "Запустить бота✅":
        # Проверяем, есть ли уже конфигурация
        if os.path.exists(CONFIG_FILE):
            bot.send_message(message.chat.id, "Бот уже настроен. Запуск...")
            asyncio.run(start_main())
        else:
            # Запрашиваем API ID
            bot.send_message(message.chat.id, "Введите ваш API ID:")
            bot.register_next_step_handler(message, get_api_id)

def get_api_id(message):
    try:
        api_id = int(message.text)
        user_data['API_ID'] = api_id
        bot.send_message(message.chat.id, "Введите ваш API Hash:")
        bot.register_next_step_handler(message, get_api_hash)
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный API ID. Введите число.")

def get_api_hash(message):
    api_hash = message.text.strip()
    user_data['API_HASH'] = api_hash
    bot.send_message(message.chat.id, "Введите ваш номер телефона (в формате +375XXXXXXXXX, +7XXXXXXXXXX):")
    bot.register_next_step_handler(message, get_phone_number)

def get_phone_number(message):
    phone_number = message.text.strip()
    user_data['PHONE_NUMBER'] = phone_number

    # Сохраняем данные в файл конфигурации
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "API_ID": user_data['API_ID'],
            "API_HASH": user_data['API_HASH'],
            "PHONE_NUMBER": user_data['PHONE_NUMBER'],
            "typing_speed": DEFAULT_TYPING_SPEED,
            "cursor_symbol": DEFAULT_CURSOR
        }, f)

    bot.send_message(message.chat.id, "Настройка завершена. Запуск бота...")
    asyncio.run(start_main())

async def start_main():
    from main import main  # Импортируем функцию main из main.py
    await main()

bot.infinity_polling()
