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
            db.cursor.execute("SELECT id, user_id, date, time, description, remind_24h, remind_1h FROM meetings")
            meetings = db.cursor.fetchall()

            for meeting in meetings:
                meeting_id, user_id, date_str, time_str, description, remind_24h, remind_1h = meeting
                meeting_datetime = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")

                # Напоминание за сутки
                if remind_24h and (meeting_datetime - timedelta(days=1)) <= now < meeting_datetime:
                    await bot.send_message(user_id, f"Напоминание: через сутки у вас встреча '{description}'.")

                # Напоминание за час
                if remind_1h and (meeting_datetime - timedelta(hours=1)) <= now < meeting_datetime:
                    await bot.send_message(user_id, f"Напоминание: через час у вас встреча '{description}'.")

            db.close()
            await asyncio.sleep(15)  # Проверяем каждую минуту

    