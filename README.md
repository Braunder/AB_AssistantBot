# AB Assistant Bot
=====================

## Описание проекта
--------------------

AB Assistant Bot - это бот, созданный для управления встречами и мероприятиями. Он позволяет пользователям добавлять, удалять и просматривать встречи, а также выдавать и удалять премиум-статус другим пользователям.

## Функционал
--------------

*   Добавление встреч с указанием даты, времени, названия и описания
*   Удаление встреч по ID
*   Просмотр всех встреч пользователя
*   Выдача премиум-статуса другим пользователям
*   Удаление премиум-статуса у других пользователей
*   Напоминания о встречах за сутки и за час до начала

## Технологии
--------------

*   Python 3.x
*   aiogram 3.x
*   sqlite3
*   asyncio

## Установка
-------------

1.  Клонировать репозиторий: `git clone https://github.com/your-repo/AB-Assistant-Bot.git`
2.  Установить зависимости: `pip install -r requirements.txt`
3.  Создать файл `config.py` с токеном бота: `TOKEN = 'your-token'`
4.  Запустить бота: `python bot.py`

## Использование
--------------

1.  Начать диалог с ботом: `/start`
2.  Добавить встречу: `Добавить встречу`
3.  Удалить встречу: `Удалить встречу`
4.  Просмотреть все встречи: `Все встречи`
5.  Выдать премиум-статус: `Выдать премиум`
6.  Удалить премиум-статус: `Удалить премиум`

## Лицензия
------------

MIT License

Copyright (c) 2025 Andrey Braunder

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
