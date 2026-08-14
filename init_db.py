import sqlite3
import os

DB_PATH = os.path.join("database", "skills.db")


def init_db():
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            domain TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    print("Database structure initialized successfully!")

if __name__ == "__main__":
    init_db()