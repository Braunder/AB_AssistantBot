import telebot
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

def start(message, bot):
    bot.send_message(message.chat.id, "Привет! Я бот для записи встреч. Используйте кнопки ниже для взаимодействия.")

def show_main_menu(message, bot):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(telebot.types.KeyboardButton("Добавить встречу"))  # Кнопка для добавления встречи
    keyboard.add(telebot.types.KeyboardButton("Список встреч"))      # Кнопка для просмотра списка встреч
    keyboard.add(telebot.types.KeyboardButton("Удалить встречу"))     # Кнопка для удаления встречи
    keyboard.add(telebot.types.KeyboardButton("Рестарт бота"))     # Кнопка для перезагрузки бота
    bot.send_message(message.chat.id, "Выберите команду:", reply_markup=keyboard)

def add_meeting(message, bot, cursor, conn):
    user_id = message.chat.id  # Получаем идентификатор пользователя
    msg = bot.send_message(user_id, "Введите название встречи:")
    bot.register_next_step_handler(msg, process_meeting_name, bot, cursor, conn, user_id)

def process_meeting_name(message, bot, cursor, conn, user_id):
    meeting_name = message.text
    msg = bot.send_message(user_id, "Введите дополнительную информацию о встрече (или оставьте пустым):")
    bot.register_next_step_handler(msg, process_additional_info, meeting_name, bot, cursor, conn, user_id)

def process_additional_info(message, meeting_name, bot, cursor, conn, user_id):
    additional_info = message.text  # Получаем дополнительную информацию
    msg = bot.send_message(user_id, "Введите дату встречи (в формате ДД-ММ-ГГГГ или ДД.ММ.ГГГГ):")
    bot.register_next_step_handler(msg, process_meeting_date, meeting_name, additional_info, bot, cursor, conn, user_id)

def process_meeting_date(message, meeting_name, additional_info, bot, cursor, conn, user_id):
    meeting_date = message.text
    try:
        # Проверка формата даты
        if '-' in meeting_date:
            datetime.strptime(meeting_date, '%d-%m-%Y')  # Формат: ДД-ММ-ГГГГ
        elif '.' in meeting_date:
            datetime.strptime(meeting_date, '%d.%m.%Y')  # Формат: ДД.ММ.ГГГГ
        else:
            raise ValueError("Неверный формат даты.")
    except ValueError:
        msg = bot.send_message(user_id, "Неверный формат даты. Попробуйте снова:")
        bot.register_next_step_handler(msg, process_meeting_date, meeting_name, additional_info, bot, cursor, conn, user_id)
        return

    msg = bot.send_message(user_id, "Введите время встречи (в формате ЧЧ:ММ):")
    bot.register_next_step_handler(msg, process_meeting_time, meeting_name, additional_info, meeting_date, bot, cursor, conn, user_id)

def process_meeting_time(message, meeting_name, additional_info, meeting_date, bot, cursor, conn, user_id):
    meeting_time = message.text
    try:
        # Проверка формата времени
        datetime.strptime(meeting_time, '%H:%M')  # Формат: ЧЧ:ММ
    except ValueError:
        msg = bot.send_message(user_id, "Неверный формат времени. Попробуйте снова:")
        bot.register_next_step_handler(msg, process_meeting_time, meeting_name, additional_info, meeting_date, bot, cursor, conn, user_id)
        return

    # Запрос частоты повторения
    process_repeat_frequency(message, meeting_name, additional_info, meeting_date, meeting_time, bot, cursor, conn, user_id)

def process_repeat_frequency(message, meeting_name, additional_info, meeting_date, meeting_time, bot, cursor, conn, user_id):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(telebot.types.KeyboardButton("1 раз"))
    keyboard.add(telebot.types.KeyboardButton("Ежедневно"))
    keyboard.add(telebot.types.KeyboardButton("Еженедельно"))
    keyboard.add(telebot.types.KeyboardButton("Ежемесячно"))
    keyboard.add(telebot.types.KeyboardButton("Ежегодно"))

    msg = bot.send_message(user_id, "Выберите частоту повторения:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, process_repeat_frequency_selection, meeting_name, additional_info, meeting_date, meeting_time, bot, cursor, conn, user_id)

def process_repeat_frequency_selection(message, meeting_name, additional_info, meeting_date, meeting_time, bot, cursor, conn, user_id):
    frequency_map = {
        "1 раз": "once",
        "Ежедневно": "daily",
        "Еженедельно": "weekly",
        "Ежемесячно": "monthly",
        "Ежегодно": "yearly"
    }
    
    frequency = message.text  # Получаем текст сообщения от пользователя
    if frequency not in frequency_map:
        msg = bot.send_message(user_id, "Неверный выбор. Пожалуйста, выберите частоту повторения снова:")
        bot.register_next_step_handler(msg, process_repeat_frequency_selection, meeting_name, additional_info, meeting_date, meeting_time, bot, cursor, conn, user_id)
        return

    # Сохранение встречи в базе данных с user_id и частотой повторения
    cursor.execute("INSERT INTO meetings (user_id, name, date, time, additional_info, repeat_frequency) VALUES (?, ?, ?, ?, ?, ?)", 
                   (user_id, meeting_name, meeting_date, meeting_time, additional_info, frequency_map[frequency]))
    conn.commit()
    bot.send_message(user_id, "Встреча добавлена с частотой повторения: " + frequency_map[frequency])
    show_main_menu(message, bot)

def list_meetings(message, bot, cursor):
    user_id = message.chat.id
    cursor.execute("SELECT name, date, time FROM meetings WHERE user_id = ? ORDER BY date, time", (user_id,))
    meetings = cursor.fetchall()
    
    if meetings:
        response = "Ваши встречи:\n"
        for meeting in meetings:
            response += f"{meeting[0]} - {meeting[1]} в {meeting[2]}\n"
    else:
        response = "У вас нет запланированных встреч."
    
    bot.send_message(user_id, response)

def delete_meeting(message, bot, cursor, conn):
    user_id = message.chat.id
    cursor.execute("SELECT id, name FROM meetings WHERE user_id = ?", (user_id,))
    meetings = cursor.fetchall()
    
    if meetings:
        response = "Выберите встречу для удаления:\n"
        for meeting in meetings:
            response += f"{meeting[0]}: {meeting[1]}\n"
        msg = bot.send_message(user_id, response)
        bot.register_next_step_handler(msg, process_delete_meeting, bot, cursor, conn, user_id)
    else:
        bot.send_message(user_id, "У вас нет запланированных встреч.")

def process_delete_meeting(message, bot, cursor, conn, user_id):
    meeting_id = message.text
    cursor.execute("DELETE FROM meetings WHERE id = ? AND user_id = ?", (meeting_id, user_id))
    conn.commit()
    bot.send_message(user_id, "Встреча удалена!")

def handle_repeating_meeting(meeting, cursor):
    user_id = meeting[1]
    meeting_name = meeting[2]
    meeting_date = meeting[3]
    meeting_time = meeting[4]
    repeat_frequency = meeting[6]  # Поле repeat_frequency

    # Преобразуем строку даты в объект datetime
    new_date = datetime.strptime(meeting_date, '%d.%m.%Y')

    # Обновляем дату в зависимости от частоты повторения
    if repeat_frequency == "daily":
        new_date += timedelta(days=1)
    elif repeat_frequency == "weekly":
        new_date += timedelta(weeks=1)
    elif repeat_frequency == "monthly":
        new_date += relativedelta(months=1)
    elif repeat_frequency == "yearly":
        new_date += relativedelta(years=1)

    # Сохраняем новую встречу в базе данных
    cursor.execute("INSERT INTO meetings (user_id, name, date, time, additional_info, repeat_frequency) VALUES (?, ?, ?, ?, ?, ?)", 
                   (user_id, meeting_name, new_date.strftime('%d.%m.%Y'), meeting_time, "", repeat_frequency))
    cursor.connection.commit()  # Сохраняем изменения

def check_meetings(bot, cursor):
    print("Функция check_meetings запущена.") 
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%d.%m.%Y")

        # Получаем все встречи, которые должны произойти сегодня или имеют повторение
        cursor.execute("SELECT * FROM meetings WHERE date = ? OR repeat_frequency IS NOT NULL", (current_date,))
        meetings = cursor.fetchall()

        print(f"Найдено встреч: {len(meetings)}. Текущее время {current_date} {current_time}")
        
        for meeting in meetings:
            user_id = meeting[1]  # Получаем user_id
            meeting_time = meeting[4]  # Извлекаем время встречи
            meeting_time = datetime.strptime(meeting_time, '%H:%M')  # Преобразуем время встречи в объект datetime
            
            # Объединяем дату и время встречи
            meeting_datetime = datetime.combine(datetime.strptime(meeting[3], '%d.%m.%Y').date(), meeting_time.time())
            time_difference = (meeting_datetime - now).total_seconds() / 60  # Разница в минутах

            print(f"Текущая дата и время: {current_date} {current_time}")
            print(f"Время встречи: {meeting[4]}")
            print(f"Разница во времени: {time_difference} минут")

            # Проверяем, если встреча начинается через 1 час или меньше и уведомление еще не отправлено
            if 0 <= time_difference < 60 and meeting[5] == 0:  # meeting[5] - это поле notified
                bot.send_message(user_id, f"Привет! Ваша встреча '{meeting[2]}' начинается в {meeting[4]} сегодня.")
                
                # Обновляем поле notified в базе данных
                cursor.execute("UPDATE meetings SET notified = 1 WHERE id = ?", (meeting[0],))
                cursor.connection.commit()  # Сохраняем изменения

                # Обработка повторяющихся встреч
                handle_repeating_meeting(meeting, cursor)

        time.sleep(15)  # Проверять каждую минуту