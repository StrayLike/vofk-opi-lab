import sqlite3
import os
from flask import g

# [ЛАБА 8] Шлях до БД
DATABASE = os.environ.get('DATABASE_PATH', 'database.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Ініціалізація БД для Docker."""
    # Гарантуємо, що папка існує
    db_dir = os.path.dirname(DATABASE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    # 💡 ФІКС: Шукаємо schema.sql у поточній папці (/app)
    schema_path = os.path.join(os.getcwd(), 'schema.sql') 
    
    with sqlite3.connect(DATABASE) as db:
        if not os.path.exists(schema_path):
            print(f"❌ ПОМИЛКА: Не знайдено {schema_path}")
            return
        
        with open(schema_path, mode='r', encoding='utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()
    print(f"✅ База даних створена: {DATABASE}")