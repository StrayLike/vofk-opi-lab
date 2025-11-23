import sqlite3
from flask import g

# Назва файлу бази даних, який створиться сам
DATABASE = 'database.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Це щоб ми могли звертатися до колонок по назві (user['email']), а не по цифрі
        db.row_factory = sqlite3.Row
    return db

def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Ця функція запускається один раз, щоб створити таблиці"""
    with sqlite3.connect(DATABASE) as db:
        with open('schema.sql', mode='r', encoding='utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()
    print("✅ База даних успішно створена!")
