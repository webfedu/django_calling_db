import os
import sys

# ------------------------------
# Django setup
# ------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calling_db.settings")

import django
django.setup()

# ------------------------------
# Імпорт моделей
# ------------------------------
from calling_app.models import Company, Region, District

# ------------------------------
# Основна логіка
# ------------------------------
for company in Company.objects.all():
    if not company.legal_address:
        continue

    address_upper = company.legal_address.upper()

    # Знаходимо область
    matched_region = None
    for region in Region.objects.all():
        if region.region.upper() in address_upper:
            matched_region = region
            break

    if matched_region:
        company.region = matched_region

        # Шукаємо район
        matched_district = None
        for district in District.objects.filter(region=matched_region):
            if district.district.upper() in address_upper:
                matched_district = district
                break

        if matched_district:
            company.district = matched_district

    company.save()
    print(f"{company.name}: region={company.region}, district={company.district}")
