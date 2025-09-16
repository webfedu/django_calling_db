import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)

DB_FILE = "db.sqlite3"
APPS = ["calling_app"]

# Видаляємо базу
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# Видаляємо старі міграції
for app in APPS:
    migrations_path = os.path.join(app, "migrations")
    if os.path.exists(migrations_path):
        for file in os.listdir(migrations_path):
            if file != "__init__.py" and file.endswith(".py"):
                os.remove(os.path.join(migrations_path, file))

# Вказуємо повний шлях до python з віртуального середовища
PYTHON_EXE = sys.executable  # бере саме той python, який зараз активний

# Створюємо нові міграції
subprocess.run([PYTHON_EXE, "manage.py", "makemigrations"])

# Застосовуємо міграції
subprocess.run([PYTHON_EXE, "manage.py", "migrate"])

print("Скидання бази завершено!")
