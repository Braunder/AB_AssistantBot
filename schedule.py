import re
import asyncio
from datetime import datetime, timedelta
from database import Database
from aiogram import Bot
from config import TOKEN

bot = Bot(token=TOKEN)

class Schedule:
    def __init__(self, name=None, start_time=None, end_time=None, duration=None, frequency=None):
        self.name = name
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.frequency = frequency

    # Функция для проверки формата даты
    def is_valid_date(date_str):
        # Проверяем формат ДД-ММ-ГГГГ или ДД.ММ.ГГГГ
        if not re.match(r"^\d{2}[\.-]\d{2}[\.-]\d{4}$", date_str):
            return False
        try:
            # Преобразуем строку в объект datetime
            date_obj = datetime.strptime(date_str, "%d-%m-%Y") if "-" in date_str else datetime.strptime(date_str, "%d.%m.%Y")
            # Проверяем, что дата не в прошлом
            return date_obj.date() >= datetime.now().date()
        except ValueError:
            return False

    # Функция для проверки формата времени
    def is_valid_time(time_str):
        # Проверяем формат ЧЧ:ММ
        if not re.match(r"^\d{2}:\d{2}$", time_str):
            return False
        try:
            # Преобразуем строку в объект времени
            datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False
        
    async def send_reminders(self):
        while True:
            db = Database('meetings.db')
            now = datetime.now()

            # Удаляем прошедшие встречи
            db.delete_past_meetings()

            # Получаем все встречи с нужными колонками
            db.cursor.execute("SELECT id, user_id, date, time, name, description, recurrence FROM meetings")
            meetings = db.cursor.fetchall()

            for meeting in meetings:
                meeting_id, user_id, date_str, time_str, name, description, recurrence = meeting
                db.cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
                username = db.cursor.fetchone()[0]
                meeting_datetime = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")

                # Напоминание за сутки
                if meeting_datetime - timedelta(days=1) <= now < meeting_datetime:
                    await bot.send_message(user_id, f"@{username}\nНапоминание:\nЧерез сутки у вас встреча '{name}'\nОписание:\n{description}")

                # Напоминание за час
                if meeting_datetime - timedelta(hours=1) <= now < meeting_datetime:
                    await bot.send_message(user_id, f"@{username}\nНапоминание:\nЧерез час у вас встреча '{name}'\nОписание:\n{description}")

                # Обработка повторяющихся встреч
                if recurrence == "Еженедельно":
                    next_meeting_datetime = meeting_datetime + timedelta(weeks=1)
                    next_meeting_date_str = next_meeting_datetime.strftime("%d.%m.%Y")
                    next_meeting_time_str = next_meeting_datetime.strftime("%H:%M")
                    
                    # Проверяем, не добавлена ли уже встреча на следующую неделю
                    db.cursor.execute("SELECT id FROM meetings WHERE user_id = ? AND date = ? AND time = ?", (user_id, next_meeting_date_str, next_meeting_time_str))
                    next_meeting_id = db.cursor.fetchone()
                    
                    if not next_meeting_id:
                        db.add_meeting(user_id, next_meeting_date_str, next_meeting_time_str, description, recurrence)
                elif recurrence == "Ежемесячно":
                    next_meeting_date_str = datetime.strptime(date_str, "%d.%m.%Y")
                    if next_meeting_date_str.month == 12:
                        next_meeting_date_str = next_meeting_date_str.replace(year=next_meeting_date_str.year + 1, month=1)
                    else:
                        next_meeting_date_str = next_meeting_date_str.replace(month=next_meeting_date_str.month + 1)
                    if next_meeting_date_str.day > 28:
                        next_meeting_date_str = next_meeting_date_str.replace(day=28)
                    next_meeting_date_str = next_meeting_date_str.strftime("%d.%m.%Y")
                    next_meeting_time_str = time_str
                    
                    # Проверяем, не добавлена ли уже встреча на следующий месяц
                    db.cursor.execute("SELECT id FROM meetings WHERE user_id = ? AND date = ? AND time = ?", (user_id, next_meeting_date_str, next_meeting_time_str))
                    next_meeting_id = db.cursor.fetchone()
                    
                    if not next_meeting_id:
                        db.add_meeting(user_id, next_meeting_date_str, next_meeting_time_str, description, recurrence)

            db.close()
            await asyncio.sleep(60)  # Проверяем каждую минуту

    