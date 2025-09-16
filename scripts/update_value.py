import sqlite3
import os

# Отримати шлях до директорії скрипта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(BASE_DIR)

# шлях до твоєї БД
db_path = os.path.join(BASE_DIR, "db.sqlite3")

# список значень, які треба замінити
bad_values = ["Аа", "-", "- -", "--", "0", "0 0", "", "- --"]

# підключення до БД
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# заміна
cursor.execute(
    f"""
    UPDATE calling_app_contactperson
    SET full_name = 'Офіс'
    WHERE full_name IN ({','.join('?'*len(bad_values))})
    """,
    bad_values
)

print(f"Оновлено рядків: {cursor.rowcount}")

conn.commit()
conn.close()
