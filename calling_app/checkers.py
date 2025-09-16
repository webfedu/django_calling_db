import re
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# -----------------------
# EDRPOU
# -----------------------
def check_edrpou(edrpou: str) -> str:
    """
    Стандартизує ЄДРПОУ:
    - видаляє всі нецифрові символи
    - робить довжину 8 цифр, додаючи нулі спереду
    - якщо некоректно (довжина > 8 або None), повертає "00000000"
    """
    if not edrpou:
        return "00000000"

    edrpou = re.sub(r'\D', '', str(edrpou))  # залишаємо тільки цифри

    if len(edrpou) < 8:
        edrpou = edrpou.zfill(8)
    elif len(edrpou) > 8:
        logging.warning(f"EDRPOU {edrpou} перевищує 8 символів, буде замінено на '00000000'")
        edrpou = "00000000"

    return edrpou

# -----------------------
# Площа
# -----------------------
def check_area(area) -> int:
    """
    Перетворює площу у ціле число.
    Якщо None або некоректне значення - повертає 0.
    """
    try:
        if area is None:
            return 0
        area = int(float(area))
        if area < 1000000:
            return int(float(area))
    except (ValueError, TypeError):
        logging.warning(f"Некоректна площа: {area}, замінено на 0")
        return 0

# -----------------------
# Телефон
# -----------------------
def check_phone(phone_number: str) -> str:
    """
    Стандартизує номер телефону у формат +380XXXXXXXXX.
    Якщо номер некоректний, повертає None
    """
    if not phone_number:
        return None

    phone_number = re.sub(r'\D', '', str(phone_number))
    length = len(phone_number)

    if length == 9:
        phone_number = "+380" + phone_number
    elif length == 10:
        phone_number = "+38" + phone_number
    elif length == 11:
        phone_number = "+3" + phone_number
    elif length == 12:
        phone_number = "+" + phone_number
    else:
        logging.warning(f"Некоректний номер {phone_number}")
        phone_number = None

    return phone_number

# -----------------------
# ПІБ/Ім’я
# -----------------------
def check_person(name: str) -> str:
    """
    Стандартизує ПІБ:
    - видаляє зайві пробіли
    - робить кожне слово з великої літери
    - прибирає зайві символи
    - спеціальні заміни (наприклад, 'аа' -> 'Офіс')
    """
    if not name or not str(name).strip():
        return "Невідома"

    name = str(name).strip()

    # Спеціальні випадки
    if name.lower() in ["аа", "н/д", "none"]:
        name = "Офіс"

    # Видаляємо всі зайві символи, залишаємо букви, пробіли, апострофи, дефіси
    name = re.sub(r"[^\w\s’'іІїЇєЄґҐа-яА-Я\-]", "", name, flags=re.UNICODE)

    # Замінюємо неправильні лапки на апостроф
    name = name.replace("’", "'").replace("`", "'")

    # Видаляємо зайві пробіли
    name = " ".join(name.split())

    # Капіталізація кожного слова
    standardized = " ".join(word.capitalize() for word in name.lower().split())

    return standardized


def is_valid_email(email):
    """
    Перевірка базового синтаксису email.
    Повертає email у нижньому регістрі, якщо він валідний, або False.
    """
    if not email:
        return False
    email = email.strip()
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if re.match(pattern, email):
        return email.lower()  # повертаємо в нижньому регістрі
    return False


def is_valid_website(site: str):
    """
    Перевіряє, чи сайт валідний і починається з www.
    Повертає нормалізований сайт або None, якщо невірний.
    """
    if not site:
        return None

    site = site.strip().lower()

    # Перевірка на www
    if not site.startswith("www."):
        return None

    # Має містити хоча б одну крапку після www
    if "." not in site[4:]:
        return None

    return site