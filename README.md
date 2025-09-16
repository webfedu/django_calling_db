# Django CallingDB Project

Цей проєкт — веб-додаток для управління компаніями, контактами та дзвінками, побудований на **Django**.

---

## 📂 Структура проєкту

calling_db/
│
├─ calling_app/ # Основний додаток
├─ manage.py # Скрипт управління Django
├─ requirements.txt # Залежності
├─ README.md # Документація
├─ .gitignore # Ігноровані файли для Git
├─ templates/ # HTML-шаблони
├─ static/ # Статичні файли (CSS, JS, картинки)
└─ media/ # Медіа-файли (завантажені користувачами)

yaml
Копіювати код

---

## ⚙️ Встановлення та запуск

1. Клонування репозиторію:
```bash
git clone https://github.com/username/django-project.git
cd django-project
Створення віртуального середовища:

bash
Копіювати код
python -m venv venv
.\venv\Scripts\activate   # Windows
Встановлення залежностей:

bash
Копіювати код
pip install -r requirements.txt
Міграції бази даних:

bash
Копіювати код
python manage.py migrate
Створення суперкористувача:

bash
Копіювати код
python manage.py createsuperuser
Запуск сервера:

bash
Копіювати код
python manage.py runserver
Відкрити браузер за адресою: http://127.0.0.1:8000/

🛠 Основні можливості
Перегляд та фільтрація компаній

Деталі контактних осіб та телефонів

Додавання компаній до холдингу

Ведення історії дзвінків

Управління складами та транспортом

📄 Git та GitHub
Ініціалізація Git:

bash
Копіювати код
git init
git add .
git commit -m "first commit"
Підключення до GitHub:

bash
Копіювати код
git remote add origin https://github.com/username/django-project.git
git branch -M main
git push -u origin main
Наступні коміти:

bash
Копіювати код
git add .
git commit -m "опис змін"
git push
📌 .gitignore
Рекомендований файл для Django:

bash
Копіювати код
# Python
*.pyc
__pycache__/

# Django
db.sqlite3
media/
staticfiles/
.env

# Logs
*.log

# Virtual environments
venv/
env/
.venv/

# IDE / Editor
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Build / Test
build/
dist/
*.spec
.coverage
.pytest_cache/
📋 requirements.txt
Мінімальні пакети для продакшн:

ini
Копіювати код
Django==5.2.5
asgiref==3.9.1
sqlparse==0.5.3
tzdata==2025.2
openpyxl==3.1.5
Можна додати requirements-dev.txt для тестів і додаткових бібліотек (pytest, colorama тощо).

🔧 Технічні деталі
Django 5.2.5

SQLite (локальна БД)

Python 3.11+

Використання openpyxl для роботи з Excel

📄 Ліцензія
Проєкт розповсюджується під ліцензією MIT.