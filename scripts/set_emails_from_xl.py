import sys
import os
import openpyxl

# ------------------------------
# Налаштування Django
# ------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calling_db.settings")

import django
django.setup()

from calling_app.models import Company, CompanyEmail
from calling_app.checkers import is_valid_email, check_edrpou, is_valid_website

# ------------------------------
# Основний код
# ------------------------------

print("BASE_DIR:", BASE_DIR)

excel_file = os.path.join(BASE_DIR, "granova.xlsx")
wb = openpyxl.load_workbook(excel_file)

for sheet in wb.worksheets:
    print(f"Опрацьовуємо вкладку: {sheet.title}")

    headers = [cell.value for cell in sheet[1]]
    if "ЄДРПОУ" not in headers or "Пошта" not in headers:
        print("Пропускаємо вкладку: відсутні стовпці 'ЄДРПОУ' або 'Пошта'")
        continue

    edrpou_idx = headers.index("ЄДРПОУ")
    email_idx = headers.index("Пошта")
    site_idx = headers.index("Сайт") if "Сайт" in headers else None

    for row in sheet.iter_rows(min_row=2, values_only=True):
        edrpou = check_edrpou(row[edrpou_idx])
        emails_str = row[email_idx]
        site_raw = row[site_idx] if site_idx is not None else None

        if not edrpou:
            continue

        # Створюємо список валідних записів (email + сайт)
        valid_entries = []

        # Додаємо email
        if emails_str:
            emails = [e.strip() for e in emails_str.split(";") if e.strip()]
            for email in emails:
                email_lower = is_valid_email(email)
                if email_lower:
                    valid_entries.append(email_lower)

        # Додаємо сайт
        valid_site = is_valid_website(site_raw)
        if valid_site:
            valid_entries.append(valid_site)

        # Якщо немає ні email, ні сайту — пропускаємо
        if not valid_entries:
            continue

        try:
            company = Company.objects.get(edrpou=str(edrpou).strip())
        except Company.DoesNotExist:
            print(f"Компанія з ЄДРПОУ {edrpou} не знайдена")
            continue

        # Записуємо усі валідні email/сайти в CompanyEmail
        for email in valid_entries:
            company_email, created = CompanyEmail.objects.get_or_create(email=email)
            company_email.companies.add(company)
            company_email.save()

print("Імпорт завершено!")
