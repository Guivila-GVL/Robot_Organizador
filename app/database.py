import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robot_organizador.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        folder_name TEXT NOT NULL,
        folder_path TEXT NOT NULL,
        category TEXT DEFAULT 'Desarrollo',
        icon TEXT DEFAULT '📁',
        color TEXT DEFAULT '#3b82f6',
        port INTEGER DEFAULT NULL,
        url TEXT DEFAULT NULL,
        description TEXT DEFAULT '',
        order_index INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Ensure order_index and onenote_url columns exist in projects
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN order_index INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE projects ADD COLUMN onenote_url TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_protocols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        item_key TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        is_enabled BOOLEAN DEFAULT 1,
        order_index INTEGER DEFAULT 0,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        priority TEXT DEFAULT 'media',
        status TEXT DEFAULT 'pending',
        milestone_type TEXT DEFAULT 'manual',
        milestone_target TEXT DEFAULT '',
        milestone_description TEXT DEFAULT '',
        milestone_result TEXT DEFAULT '',
        result_image_url TEXT DEFAULT '',
        order_index INTEGER DEFAULT 0,
        queue_order INTEGER DEFAULT 0,
        progress_pct INTEGER DEFAULT 0,
        current_step TEXT DEFAULT '',
        launched_at TEXT DEFAULT NULL,
        created_at TEXT NOT NULL,
        completed_at TEXT DEFAULT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );
    """)

    # Migraciones seguras para columnas nuevas en tasks
    for col_def in [
        "queue_order INTEGER DEFAULT 0",
        "progress_pct INTEGER DEFAULT 0",
        "current_step TEXT DEFAULT ''",
        "launched_at TEXT DEFAULT NULL",
        "notified_stages TEXT DEFAULT ''",
        "parent_task_id INTEGER DEFAULT NULL",
        "is_subtask BOOLEAN DEFAULT 0"
    ]:
        try:
            cursor.execute(f"ALTER TABLE tasks ADD COLUMN {col_def}")
        except sqlite3.OperationalError:
            pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        author TEXT DEFAULT 'Usuario',
        text TEXT NOT NULL,
        image_url TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # Seed default settings if not present
    cursor.execute("SELECT key FROM settings WHERE key = 'telegram_bot_token'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings (key, value) VALUES ('telegram_bot_token', '8691202872:AAGolw9n9HOGSos7NTlYHZJg-AeW4cMNzgU')")
        cursor.execute("INSERT INTO settings (key, value) VALUES ('telegram_chat_id', '7156474626')")
        cursor.execute("INSERT INTO settings (key, value) VALUES ('n8n_webhook_url', 'http://localhost:5678/webhook/robot-task-completed')")
        cursor.execute("INSERT INTO settings (key, value) VALUES ('notify_telegram_enabled', 'true')")
        cursor.execute("INSERT INTO settings (key, value) VALUES ('notify_via_n8n', 'false')")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
