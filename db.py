import sqlite3
from datetime import datetime

DB_NAME = "project_management.db"

def connect():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = connect()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER UNIQUE,
        name TEXT,
        is_super_admin INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT,
        customer TEXT,
        pic_user_id INTEGER,
        status TEXT,
        start_date TEXT,
        end_date TEXT,
        telegram_group_id INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS project_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        file_name TEXT,
        telegram_file_id TEXT,
        uploaded_at TEXT
    )
    """)

    conn.commit()
    conn.close()
