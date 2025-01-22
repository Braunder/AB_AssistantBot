import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """Создает таблицы users и meetings, если они не существуют."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                premium BOOL NOT NULL DEFAULT 0
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                description TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        self.conn.commit()

    def add_user(self, user_id, username):
        """Добавляет пользователя в таблицу users, если его еще нет."""
        self.cursor.execute("""
            INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)
        """, (user_id, username))
        self.conn.commit()

    def add_meeting(self, user_id, date, time, description):
        """Добавляет встречу в таблицу meetings."""
        self.cursor.execute("""
            INSERT INTO meetings (user_id, date, time, description)
            VALUES (?, ?, ?, ?)
        """, (user_id, date, time, description))
        self.conn.commit()

    def delete_meeting(self, meeting_id, user_id):
        """Удаляет встречу по ID и user_id."""
        self.cursor.execute("""
            DELETE FROM meetings WHERE id = ? AND user_id = ?
        """, (meeting_id, user_id))
        self.conn.commit()

    def get_all_meetings(self, user_id):
        """Возвращает все встречи для указанного пользователя."""
        self.cursor.execute("""
            SELECT id, date, time, description FROM meetings WHERE user_id = ?
        """, (user_id,))
        return self.cursor.fetchall()

    def get_meeting_count(self, user_id):
        """Возвращает количество встреч для указанного пользователя."""
        self.cursor.execute("""
            SELECT COUNT(*) FROM meetings WHERE user_id = ?
        """, (user_id,))
        return self.cursor.fetchone()[0]

    def is_premium(self, user_id):
        """Проверяет, является ли пользователь премиум."""
        self.cursor.execute("""
            SELECT premium FROM users WHERE id = ?
        """, (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else False

    def grant_premium_by_username(self, username):
        """Выдает премиум-статус пользователю по username."""
        self.cursor.execute("""
            UPDATE users SET premium = 1 WHERE username = ?
        """, (username,))
        self.conn.commit()

    def revoke_premium_by_username(self, username):
        """Удаляет премиум-статус у пользователя по username."""
        self.cursor.execute("""
            UPDATE users SET premium = 0 WHERE username = ?
        """, (username,))
        self.conn.commit()

    def is_premium_by_username(self, username):
        """Проверяет, является ли пользователь премиум по username."""
        self.cursor.execute("""
            SELECT premium FROM users WHERE username = ?
        """, (username,))
        result = self.cursor.fetchone()
        return result[0] if result else False

    def delete_past_meetings(self):
        """Удаляет прошедшие встречи."""
        now = datetime.now().strftime("%d-%m-%Y %H:%M")
        self.cursor.execute("""
            DELETE FROM meetings
            WHERE date || ' ' || time < ?
        """, (now,))
        self.conn.commit()

    def close(self):
        """Закрывает соединение с базой данных."""
        self.conn.close()