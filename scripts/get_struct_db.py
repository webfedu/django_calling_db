import sqlite3
import os

# Отримати шлях до директорії скрипта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(BASE_DIR)


db = os.path.join(BASE_DIR, "db.sqlite3")

conn = sqlite3.connect(db)
cursor = conn.cursor()

# Показати всі таблиці
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

# Показати схему конкретної таблиці
for row in cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';"):
    print(row[0])

conn.close()