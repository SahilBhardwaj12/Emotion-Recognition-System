import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "mood_history.db")

def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            emotion    TEXT    NOT NULL,
            confidence REAL    NOT NULL,
            time       TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_emotion(emotion: str, confidence: float):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO history (emotion, confidence, time) VALUES (?, ?, ?)",
        (emotion, round(confidence, 4), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def get_history(limit: int = 50) -> list:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT emotion, confidence, time FROM history ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_emotion_counts() -> dict:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT emotion, COUNT(*) as count FROM history GROUP BY emotion ORDER BY count DESC"
    ).fetchall()
    conn.close()
    return {row["emotion"]: row["count"] for row in rows}

init_db()