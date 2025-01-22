import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import TOKEN
from database import Database
from schedule import Schedule as sc

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

class MeetingForm(StatesGroup):
    date = State()
    time = State()
    description = State()

class GrantPremiumForm(StatesGroup):
    username = State()

class RevokePremiumForm(StatesGroup):
    username = State()

def get_start_keyboard(user_id):
    """Создает клавиатуру с кнопками в зависимости от user_id."""
    keyboard = [
        [KeyboardButton(text="Добавить встречу")],
        [KeyboardButton(text="Удалить встречу")],
        [KeyboardButton(text="Все встречи")]
    ]
    
    # Если пользователь является администратором, добавляем дополнительные кнопки
    if user_id == 1111989444:
        keyboard.append([KeyboardButton(text="Выдать премиум")])
        keyboard.append([KeyboardButton(text="Удалить премиум")])
    
    # Добавляем кнопку "Вернуться в начало"
    keyboard.append([KeyboardButton(text="Вернуться в начало")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,  # Автоматически изменять размер клавиатуры
        one_time_keyboard=True  # Скрыть клавиатуру после выбора
    )

@dp.message(Command("start"))
async def send_keyboard(message: Message):
    """Обработчик команды /start."""
    db = Database('meetings.db')
    db.add_user(message.from_user.id, message.from_user.username)
    db.close()

    await message.answer("Привет, я ваш телеграм-бот!")
    
    # Создаем меню с кнопками в зависимости от user_id
    keyboard = get_start_keyboard(message.from_user.id)
    
    await message.answer("Выберите опцию:", reply_markup=keyboard)

@dp.message(lambda message: message.text == "Добавить встречу")
async def add_meeting(message: Message, state: FSMContext):
    """Начинает процесс добавления встречи."""
    await bot.delete_message(message.chat.id, message.message_id)
    
    db = Database('meetings.db')
    user_id = message.from_user.id
    
    # Проверяем лимит встреч для обычных пользователей
    if user_id != 1111989444:
        meeting_count = db.get_meeting_count(user_id)
        is_premium = db.is_premium(user_id)
        max_meetings = 20 if is_premium else 5
        
        if meeting_count >= max_meetings:
            await message.answer(
                f"Вы достигли лимита встреч ({max_meetings}). Удалите старые встречи или приобретите премиум-статус.",
                reply_markup=ReplyKeyboardRemove()
            )
            db.close()
            return
    
    await message.answer("Введите дату встречи (формат: ДД-ММ-ГГГГ или ДД.ММ.ГГГГ):")
    await state.set_state(MeetingForm.date)
    db.close()

@dp.message(MeetingForm.date)
async def process_date(message: Message, state: FSMContext):
    """Обрабатывает ввод даты."""
    if message.text == "Вернуться в начало":
        await return_to_start(message, state)
        return
    
    if not sc.is_valid_date(message.text):
        await message.answer("Некорректная дата. Пожалуйста, введите дату в формате ДД-ММ-ГГГГ или ДД.ММ.ГГГГ, и она должна быть не в прошлом.")
        return
    
    # Преобразуем дату в формат ДД.ММ.ГГГГ
    date_str = message.text
    if "-" in date_str:
        date_obj = datetime.strptime(date_str, "%d-%m-%Y")
        date_str = date_obj.strftime("%d.%m.%Y")
    
    await state.update_data(date=date_str)
    await message.answer("Введите время встречи (формат: ЧЧ:ММ):")
    await state.set_state(MeetingForm.time)

@dp.message(MeetingForm.time)
async def process_time(message: Message, state: FSMContext):
    """Обрабатывает ввод времени."""
    if message.text == "Вернуться в начало":
        await return_to_start(message, state)
        return
    
    if not sc.is_valid_time(message.text):
        await message.answer("Некорректное время. Пожалуйста, введите время в формате ЧЧ:ММ.")
        return

    user_data = await state.get_data()
    date_str = user_data['date']
    time_str = message.text

    # Проверяем, если дата сегодня, то время должно быть в будущем
    date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    time_obj = datetime.strptime(time_str, "%H:%M").time()
    if date_obj.date() == datetime.now().date() and time_obj <= datetime.now().time():
        await message.answer("Время встречи должно быть в будущем.")
        return

    await state.update_data(time=time_str)
    await message.answer("Введите описание встречи:")
    await state.set_state(MeetingForm.description)

@dp.message(MeetingForm.description)
async def process_description(message: Message, state: FSMContext):
    """Обрабатывает ввод описания и добавляет встречу в базу данных."""
    if message.text == "Вернуться в начало":
        await return_to_start(message, state)
        return
    
    user_data = await state.get_data()
    db = Database('meetings.db')
    db.add_meeting(
        message.from_user.id,
        user_data['date'],
        user_data['time'],
        message.text
    )
    
    await message.answer("Встреча успешно добавлена!", reply_markup=get_start_keyboard(message.from_user.id))
    await state.clear()
    db.close()

@dp.message(lambda message: message.text == "Удалить встречу")
async def delete_meeting(message: Message):
    """Начинает процесс удаления встречи."""
    await bot.delete_message(message.chat.id, message.message_id)
    
    db = Database('meetings.db')
    meetings = db.get_all_meetings(message.from_user.id)
    if meetings:
        meetings_list = "\n".join([f"ID: {meeting[0]}, Дата: {meeting[1]}, Время: {meeting[2]}, Описание: {meeting[3]}" for meeting in meetings])
        await message.answer(f"Ваши встречи:\n{meetings_list}\nВведите ID встречи для удаления или нажмите 'Вернуться в начало':", reply_markup=get_start_keyboard(message.from_user.id))
    else:
        await message.answer("У вас нет встреч для удаления.")
    db.close()

@dp.message(lambda message: message.text.isdigit())
async def process_delete_meeting(message: Message, state: FSMContext):
    """Удаляет встречу по ID, если она существует."""
    current_state = await state.get_state()
    
    # Проверяем, находится ли пользователь в процессе удаления встречи
    if current_state != "MeetingForm:date" and current_state != "MeetingForm:time" and current_state != "MeetingForm:description":
        db = Database('meetings.db')
        
        # Получаем все встречи пользователя
        meetings = db.get_all_meetings(message.from_user.id)
        
        # Проверяем, существует ли встреча с таким ID
        meeting_ids = [str(meeting[0]) for meeting in meetings]  # Преобразуем ID встреч в строки
        if message.text in meeting_ids:
            db.delete_meeting(message.text, message.from_user.id)
            await message.answer("Встреча успешно удалена!", reply_markup=get_start_keyboard(message.from_user.id))
        else:
            # Не отправляем сообщение, если встреча не найдена
            pass
        
        db.close()
    else:
        # Если пользователь находится в процессе добавления встречи, игнорируем сообщение
        pass

@dp.message(lambda message: message.text == "Все встречи")
async def show_all_meetings(message: Message):
    """Показывает все встречи пользователя."""
    await bot.delete_message(message.chat.id, message.message_id)
    
    db = Database('meetings.db')
    meetings = db.get_all_meetings(message.from_user.id)
    if meetings:
        meetings_list = "\n".join([f"ID: {meeting[0]}, Дата: {meeting[1]}, Время: {meeting[2]}, Описание: {meeting[3]}" for meeting in meetings])
        await message.answer(f"Ваши встречи:\n{meetings_list}")
    else:
        await message.answer("У вас нет встреч.")
    db.close()

@dp.message(lambda message: message.text == "Выдать премиум")
async def grant_premium(message: Message, state: FSMContext):
    """Начинает процесс выдачи премиум-статуса."""
    await bot.delete_message(message.chat.id, message.message_id)
    await message.answer("Введите username пользователя, которому хотите выдать премиум:")
    await state.set_state(GrantPremiumForm.username)

@dp.message(lambda message: message.text == "Удалить премиум")
async def revoke_premium(message: Message, state: FSMContext):
    """Начинает процесс удаления премиум-статуса."""
    await bot.delete_message(message.chat.id, message.message_id)
    await message.answer("Введите username пользователя, у которого хотите удалить премиум:")
    await state.set_state(RevokePremiumForm.username)

@dp.message(GrantPremiumForm.username)
async def process_grant_premium_username(message: Message, state: FSMContext):
    """Выдает премиум-статус пользователю."""
    username = message.text
    db = Database('meetings.db')
    db.grant_premium_by_username(username)
    
    # Оповещаем пользователя о выдаче премиум-статуса
    db.cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = db.cursor.fetchone()
    if user:
        user_id = user[0]
        await bot.send_message(user_id, "🎉 Вам выдан премиум-статус! Теперь вы можете добавлять до 20 встреч.")
    
    await message.answer(f"Премиум-статус успешно выдан пользователю {username}.")
    await state.clear()
    db.close()

@dp.message(RevokePremiumForm.username)
async def process_revoke_premium_username(message: Message, state: FSMContext):
    """Удаляет премиум-статус у пользователя."""
    username = message.text
    db = Database('meetings.db')
    db.revoke_premium_by_username(username)
    
    # Оповещаем пользователя об удалении премиум-статуса
    db.cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = db.cursor.fetchone()
    if user:
        user_id = user[0]
        await bot.send_message(user_id, "😔 Ваш премиум-статус был удален. Теперь вы можете добавлять до 5 встреч.")
    
    await message.answer(f"Премиум-статус успешно удален у пользователя {username}.")
    await state.clear()
    db.close()

@dp.message(lambda message: message.text == "Вернуться в начало")
async def return_to_start(message: Message, state: FSMContext):
    """Возвращает пользователя в главное меню."""
    await bot.delete_message(message.chat.id, message.message_id)
    await state.clear()
    await message.answer("Выберите действие:", reply_markup=get_start_keyboard(message.from_user.id))

async def main():
    """Запуск бота."""
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())