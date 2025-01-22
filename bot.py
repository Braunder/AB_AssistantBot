import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
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
    reminder = State()

class GrantPremiumForm(StatesGroup):
    username = State()

class RevokePremiumForm(StatesGroup):
    username = State()


def get_reminder_keyboard():
    keyboard_buttons = [
        [InlineKeyboardButton(text="За сутки", callback_data='reminder_24h')],
        [InlineKeyboardButton(text="За час", callback_data='reminder_1h')],
        [InlineKeyboardButton(text="Оба напоминания", callback_data='reminder_both')],
        [InlineKeyboardButton(text="Без напоминаний", callback_data='reminder_none')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

@dp.message(Command("start"))
async def send_keyboard(message: Message):
    db = Database('meetings.db')
    db.add_user(message.from_user.id, message.from_user.username)
    db.close()

    await message.answer("Привет, я ваш телеграм-бот!")
    
    add_meeting_button = InlineKeyboardButton(text="Добавить встречу", callback_data='add_meeting')
    del_meeting_button = InlineKeyboardButton(text="Удалить встречу", callback_data='del_meeting')
    all_meeting_button = InlineKeyboardButton(text="Все встречи", callback_data='all_meeting')
    
    keyboard_buttons = [[add_meeting_button, del_meeting_button, all_meeting_button]]
    
    if message.from_user.id == 1111989444:
        grant_premium_button = InlineKeyboardButton(text="Выдать премиум", callback_data='grant_premium')
        revoke_premium_button = InlineKeyboardButton(text="Удалить премиум", callback_data='revoke_premium')
        keyboard_buttons.append([grant_premium_button, revoke_premium_button])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await bot.send_message(message.chat.id, "Выберите опцию:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == 'add_meeting')
async def add_meeting(callback_query: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    
    # Открываем соединение с базой данных
    db = Database('meetings.db')
    
    # Проверяем, является ли пользователь исключением (user_id = 1111989444)
    user_id = callback_query.from_user.id
    if user_id != 1111989444:
        # Проверяем количество встреч пользователя
        meeting_count = db.get_meeting_count(user_id)
        is_premium = db.is_premium(user_id)
        
        # Ограничения для обычных и премиум пользователей
        max_meetings = 20 if is_premium else 5
        
        # Если лимит встреч достигнут
        if meeting_count >= max_meetings:
            await bot.send_message(
                user_id,
                f"Вы достигли лимита встреч ({max_meetings}). Удалите старые встречи или приобретите премиум-статус."
            )
            db.close()
            return
    
    # Если лимит не достигнут или пользователь исключение, продолжаем процесс добавления встречи
    await bot.send_message(user_id, "Введите дату встречи (формат: ДД-ММ-ГГГГ или ДД.ММ.ГГГГ):")
    await state.set_state(MeetingForm.date)
    
    # Закрываем соединение с базой данных
    db.close()

@dp.message(MeetingForm.date)
async def process_date(message: Message, state: FSMContext):
    if not sc.is_valid_date(message.text):
        await message.answer("Некорректная дата. Пожалуйста, введите дату в формате ДД-ММ-ГГГГ или ДД.ММ.ГГГГ, и она должна быть не в прошлом.")
        return
    
    # Преобразуем дату в формат ДД.ММ.ГГГГ, если она введена через дефис
    date_str = message.text
    if "-" in date_str:
        date_obj = datetime.strptime(date_str, "%d-%m-%Y")
        date_str = date_obj.strftime("%d.%m.%Y")
    
    # Сохраняем дату в состоянии
    await state.update_data(date=date_str)
    
    await message.answer("Введите время встречи (формат: ЧЧ:ММ):")
    await state.set_state(MeetingForm.time)

@dp.message(MeetingForm.time)
async def process_time(message: Message, state: FSMContext):
    if not sc.is_valid_time(message.text):
        await message.answer("Некорректное время. Пожалуйста, введите время в формате ЧЧ:ММ.")
        return

    user_data = await state.get_data()
    date_str = user_data['date']
    time_str = message.text

    # Преобразуем дату и время в объект datetime
    date_obj = datetime.strptime(date_str, "%d-%m-%Y") if "-" in date_str else datetime.strptime(date_str, "%d.%m.%Y")
    time_obj = datetime.strptime(time_str, "%H:%M").time()

    # Проверяем, если дата сегодня, то время должно быть в будущем
    if date_obj.date() == datetime.now().date() and time_obj <= datetime.now().time():
        await message.answer("Время встречи должно быть в будущем.")
        return

    await state.update_data(time=time_str)
    await message.answer("Введите описание встречи:")
    await state.set_state(MeetingForm.description)

@dp.message(MeetingForm.description)
async def process_description(message: Message, state: FSMContext):
    # Сохраняем описание встречи
    await state.update_data(description=message.text)
    
    # Отправляем клавиатуру для выбора напоминания
    await message.answer("Выберите напоминание:", reply_markup=get_reminder_keyboard())
    await state.set_state(MeetingForm.reminder)

@dp.callback_query(MeetingForm.reminder)
async def process_reminder(callback_query: CallbackQuery, state: FSMContext):
    reminder_choice = callback_query.data
    user_data = await state.get_data()
    db = Database('meetings.db')
    
    # Определяем, какие напоминания нужно установить
    remind_24h = reminder_choice in ['reminder_24h', 'reminder_both']
    remind_1h = reminder_choice in ['reminder_1h', 'reminder_both']
    
    # Добавляем встречу в базу данных с информацией о напоминаниях
    db.add_meeting(
        callback_query.from_user.id,
        user_data['date'],
        user_data['time'],
        user_data['description'],
        remind_24h,
        remind_1h
    )
    
    # Удаляем сообщение с клавиатурой
    reminder_message_id = user_data.get('reminder_message_id')
    if reminder_message_id:
        await bot.delete_message(callback_query.from_user.id, reminder_message_id)
    
    # Оповещаем пользователя
    await bot.send_message(callback_query.from_user.id, "Встреча успешно добавлена!")
    await state.clear()
    db.close()

@dp.callback_query(lambda c: c.data == 'del_meeting')
async def delete_meeting(callback_query: CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    db = Database('meetings.db')
    meetings = db.get_all_meetings(callback_query.from_user.id)
    if meetings:
        meetings_list = "\n".join([f"{meeting[0]}: {meeting[1]} {meeting[2]} - {meeting[3]}" for meeting in meetings])
        await bot.send_message(callback_query.from_user.id, f"Ваши встречи:\n{meetings_list}\nВведите ID встречи для удаления:")
    else:
        await bot.send_message(callback_query.from_user.id, "У вас нет встреч для удаления.")
    db.close()

@dp.message(lambda message: message.text.isdigit())
async def process_delete_meeting(message: Message):
    db = Database('meetings.db')
    db.delete_meeting(message.text, message.from_user.id)
    await message.answer("Встреча успешно удалена!")
    db.close()

@dp.callback_query(lambda c: c.data == 'all_meeting')
async def show_all_meetings(callback_query: CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    db = Database('meetings.db')
    meetings = db.get_all_meetings(callback_query.from_user.id)
    if meetings:
        meetings_list = "\n".join([f"{meeting[1]} {meeting[2]} - {meeting[3]}" for meeting in meetings])
        await bot.send_message(callback_query.from_user.id, f"Ваши встречи:\n{meetings_list}")
    else:
        await bot.send_message(callback_query.from_user.id, "У вас нет встреч.")
    db.close()

@dp.callback_query(lambda c: c.data == 'grant_premium')
async def grant_premium(callback_query: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите username пользователя, которому хотите выдать премиум:")
    await state.set_state(GrantPremiumForm.username)

@dp.callback_query(lambda c: c.data == 'revoke_premium')
async def revoke_premium(callback_query: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Введите username пользователя, у которого хотите удалить премиум:")
    await state.set_state(RevokePremiumForm.username)

@dp.message(GrantPremiumForm.username)
async def process_grant_premium_username(message: Message, state: FSMContext):
    username = message.text
    db = Database('meetings.db')
    
    # Выдаем премиум-статус
    db.grant_premium_by_username(username)
    
    # Получаем user_id пользователя по username
    db.cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = db.cursor.fetchone()
    
    if user:
        user_id = user[0]
        # Оповещаем пользователя о выдаче премиум-статуса
        await bot.send_message(user_id, "🎉 Вам выдан премиум-статус! Теперь вы можете добавлять до 20 встреч.")
    
    await message.answer(f"Премиум-статус успешно выдан пользователю {username}.")
    await state.clear()
    db.close()

@dp.message(RevokePremiumForm.username)
async def process_revoke_premium_username(message: Message, state: FSMContext):
    username = message.text
    db = Database('meetings.db')
    
    # Удаляем премиум-статус
    db.revoke_premium_by_username(username)
    
    # Получаем user_id пользователя по username
    db.cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = db.cursor.fetchone()
    
    if user:
        user_id = user[0]
        # Оповещаем пользователя об удалении премиум-статуса
        await bot.send_message(user_id, "😔 Ваш премиум-статус был удален. Теперь вы можете добавлять до 5 встреч.")
    
    await message.answer(f"Премиум-статус успешно удален у пользователя {username}.")
    await state.clear()
    db.close()

async def main():
    schedule_instance = sc()
    asyncio.create_task(schedule_instance.send_reminders())
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    asyncio.run(main())