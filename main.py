import telebot
import threading
import sqlite3
from commands import start, add_meeting, list_meetings, delete_meeting, show_main_menu, check_meetings

API_TOKEN = '7954557300:AAG7K8KnYpy5G1zXp0L7VX6iPgrm7ykXwrM'  # Замените на ваш токен
bot = telebot.TeleBot(API_TOKEN)

# Подключение к базе данных
conn = sqlite3.connect('meetings.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы для встреч
cursor.execute('''
CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    additional_info TEXT,
    notified INTEGER DEFAULT 0,
    repeat_frequency TEXT DEFAULT 'once'  -- Новое поле для частоты повторения
)
''')
conn.commit()

# Регистрация обработчиков команд
@bot.message_handler(commands=['start'])
@bot.message_handler(func=lambda message: message.text.lower() == "рестарт бота")
def handle_start(message):
    start(message, bot)
    show_main_menu(message, bot)

@bot.message_handler(commands=['add'])
@bot.message_handler(func=lambda message: message.text.lower() == "добавить встречу")
def handle_add(message):
    add_meeting(message, bot, cursor, conn)

@bot.message_handler(commands=['list'])
@bot.message_handler(func=lambda message: message.text.lower() == "список встреч")
def handle_list(message):
    list_meetings(message, bot, cursor)

@bot.message_handler(commands=['delete'])
@bot.message_handler(func=lambda message: message.text.lower() == "удалить встречу")
def handle_delete(message):
    delete_meeting(message, bot, cursor, conn)

if __name__ == '__main__':
    threading.Thread(target=check_meetings, args=(bot, cursor), daemon=True).start()
    bot.polling(none_stop=True)