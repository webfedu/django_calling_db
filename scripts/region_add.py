import sys
import os
import django
import json

# Додаємо робочий каталог (там, де лежить manage.py)
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

# Встановлюємо правильний settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calling_db.settings")
django.setup()

from calling_app.models import Region, District

# Завантажуємо словник з JSON (той, що ти сформував раніше)
with open("regions_districts.json", "r", encoding="utf-8") as f:
    regions_dict = json.load(f)

for region_name, districts in regions_dict.items():
    # створюємо область, якщо її ще нема
    region, _ = Region.objects.get_or_create(region=region_name)

    for district_name in districts:
        District.objects.get_or_create(region=region, district=district_name)

print("✅ Області та райони успішно додані в БД!")

