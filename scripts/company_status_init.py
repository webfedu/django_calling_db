import os
import sys
import django

# додаємо шлях до кореня проекту (де лежить manage.py)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calling_db.settings")
django.setup()

from calling_app.models import CompanyStatus

CompanyStatus.objects.get_or_create(status_name="active")
CompanyStatus.objects.get_or_create(status_name="nonactive")