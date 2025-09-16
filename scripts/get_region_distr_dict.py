import sqlite3
import re
import json
from collections import defaultdict
import os

# Отримати шлях до директорії скрипта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(BASE_DIR)


old_db = os.path.join(BASE_DIR, "old_db.sqlite3")

# Підключення до БД
conn = sqlite3.connect(old_db)
cursor = conn.cursor()

# Вибірка адрес з таблиці
cursor.execute("SELECT address FROM companies")
rows = cursor.fetchall()

# Регулярки для пошуку
region_pattern = re.compile(r"(\w+)\s*обл")
district_pattern = re.compile(r"(\w+)\s*р-н")

result = defaultdict(set)

for row in rows:
    addr = row[0]

    # пропускаємо None або пусті рядки
    if not addr:
        continue

    region_match = region_pattern.search(addr)
    district_match = district_pattern.search(addr)

    if region_match and district_match:
        region = region_match.group(1)
        district = district_match.group(1)
        result[region].add(district)
    else:
        # для відладки: показати що не вдалося розпарсити
        print("⚠️ Не вдалося розпізнати адресу:", addr)

# перетворюємо множини на списки
final_result = {k: sorted(list(v)) for k, v in result.items()}

# Збереження у JSON
with open("regions_districts.json", "w", encoding="utf-8") as f:
    json.dump(final_result, f, ensure_ascii=False, indent=4)

print("✅ Дані збережено у regions_districts.json")

