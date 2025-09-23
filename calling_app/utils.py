from typing import Optional, Tuple, Set, Type, List
from django.apps import apps
from django.contrib import messages
from django.db.models import (Model, Q, QuerySet, CharField, TextField, ForeignKey, OneToOneField, 
                              ManyToManyField, ManyToManyRel, Sum, Max, Min)
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpRequest
from .models import Phone, Company, ContactPerson, Call, Holding
from .forms import PhoneForm, ContactForm, HoldingForm
from django.utils import timezone
import datetime

QsHash = None
QsListHash = []
SearchHash = {}


def get_company_contact(edrpou: str, contact_pk: int) -> Tuple[Company, ContactPerson]:
    """
    Повертає кортеж (company, contact) або  додає до компанії
    контакт 'Офіс' або кидає 404 один раз.
    Забезпечує безпечне отримання контактної особи, яка належить компанії.
    """
    company = get_object_or_404(Company, edrpou=edrpou)
    contact = get_object_or_404(ContactPerson, pk=contact_pk)

# Перевірка належності контакту компанії
    if not company.contacts.filter(pk=contact_pk).exists():
        contact_pk = 1
        contact = get_object_or_404(ContactPerson, pk=contact_pk)
        if not company.contacts.filter(pk=contact_pk).exists():
            company.contacts.add(contact)
            company.save()
            if not company.contacts.filter(pk=contact_pk).exists():
                raise ValueError(f"Contact {contact_pk} не належить компанії {edrpou}")
    return company, contact


def get_filtered_sorted_companies(
    company_headers: List[str],
    search: str,
    fast_search: bool,
    hectares_val: Optional[str],
    hectares_op: Optional[str],
    sort: str,
    direction: str,
) -> QuerySet[Company]:
    
    """
    Побудувати queryset компаній з урахуванням пошуку, фільтрації та сортування.

    :param search: рядок для пошуку (частковий збіг по текстових полях і зв’язках)
    :param hectares_val: значення для фільтрації по гектарах (очікується число у вигляді рядка)
    :param hectares_op: оператор для порівняння гектарів ('<', '>', '<=', '>=')
    :param sort: поле для сортування (має бути у company_headers)
    :param direction: напрямок сортування ('asc' або 'desc')
    :return: відфільтрований та відсортований QuerySet компаній
    """
    global SearchHash
    global QsHash
    global QsListHash

    search_hash = {"search": search,
                  "hectares_val": hectares_val, 
                  "hectares_op": hectares_op,
                  "fast_search": fast_search,
                  }
    print(search_hash)
    print(SearchHash)
    
    if search_hash == SearchHash:
        qs = QsHash
        qs_list = QsListHash
        qs_list.sort(key=lambda c: _sort_key(c, sort), reverse=(direction == "desc"))
        print("QsHash")

    else:
        qs: QuerySet[Company] = Company.objects.all()
        qs = Company.objects.annotate(
            last_call=Max("calls__datetime"),
            next_call=Min("planned_calls__planned_datetime", 
                        filter=Q(planned_calls__status="on")  # враховуємо тільки активні плани
                            )
            )
        if not fast_search:
            qs = search_in_queryset(qs, search) # --- Пошук ---
        else:
            qs = quick_search_companies(search)
        
        qs = _filter_by_hectares(qs, hectares_val, hectares_op) # --- Фільтр по гектарах ---

        

        qs = _sort_queryset(qs, sort, direction, company_headers) # --- Сортування ---
        
        qs_list = list(qs)
        SearchHash = search_hash
    
    QsHash = qs
    QsListHash = qs_list

    print("QsHash")
    return qs, qs_list




def get_or_create_contact_in_company(contact_form: ContactForm, company: str) -> Tuple[ContactPerson, str]:
    
    contact = None
    
    if contact_form.is_valid():
        name = contact_form.cleaned_data["full_name"]
        position = contact_form.cleaned_data.get("position", "")
        contact, message = _get_or_create_contact_by_name_in_company(name, position, company)
    else: 
        message = "Форма контакту заповнена невірно!"
    
    return contact, message


def _get_or_create_contact_by_name_in_company(name: str, position: str, company: Company) -> Tuple[ContactPerson, str]:
    """
    Повертає контакт з БД або створює новий, додає його до компанії.
    Повертає кортеж (contact, message).
    Якщо передано request, можна додавати повідомлення через messages.
    """
    contact = ContactPerson.objects.filter(full_name=name).first()
    if contact:
        message = (f"Контакт існував, прив'язано до компанії, попередня посада '{contact.position}.\n"
                   f"Якщо це не та особа, то можна її видалити з компанії і створити іншу з приміткою.")
    else:
        contact = ContactPerson.objects.create(full_name=name)
        message = "Контакт створено!"

    contact.position = position
    contact.save()
    contact.companies.add(company)
    
    return contact, message


def save_contact_with_form(co_form: ContactForm) -> str:
    if co_form.is_valid():
        co_form.save()
        message = "Контакт оновлено успішно"
    else:
        message = "Форма контакту невірна, виникла помилка"
    return message


def delete_contact_from_company(contact: ContactPerson, company: Company) -> str:
    message = f"Помилка, такої компанії не існує - {company}"
    if company:
        contact.companies.remove(company)
        message = "Контактна особа видалена з компанії"
    return message


def update_phone_in_company_contact_by_index(
                                                ph_form: PhoneForm,
                                                contact: ContactPerson,
                                                company: Company,
                                                ph_forms: List[PhoneForm],
                                                index: int,
                                            ) -> Tuple[List[PhoneForm], str]:
    """
    Оновлює телефон у контакті та компанії за індексом у списку форм.
    Повертає оновлений список форм і повідомлення для користувача.
    """
    ph_forms[index] = ph_form

    if not ph_form.is_valid():
        return ph_forms, "Телефон введено некоректно."

    number = ph_form.cleaned_data.get("number")
    status = ph_form.cleaned_data.get("status")

    phone, _ = Phone.objects.get_or_create(number=number, defaults={"status": status, "contact": contact},)

    # оновлення полів
    phone.contact = contact
    phone.status = status
    phone.save()
    phone.companies.add(company)

    # перебудовуємо форму з оновленим інстансом
    ph_forms[index] = PhoneForm(instance=phone, prefix=ph_form.prefix)

    return ph_forms, f"✅ Додано/оновлено телефон {number} (статус: {status})"



def delete_phone_from_contact_company(contact: ContactPerson,
                                        cp_contact: bool,
                                        cp_company: bool, 
                                        company: Company, 
                                        phones_qs: QuerySet, 
                                        index: int) -> str:
    
    phone = phones_qs[index]
    if not phone.number:
        message = "Телефон не існує..."
        return message

    if not(cp_contact or cp_company):
        message = "Потрібно відмітити галочкою з відки видалити телефон..."
        return message

    if cp_contact:
        phone.contact_id = None
        message = f"Телефон {phone.number} видалено з контакту {contact.full_name}"

    if cp_company:
        phone.companies.remove(company)
        message = f"Телефон {phone.number} видалено з компанії {company.name}"

    phone.save()


def get_index_from_post(key: str, prefix: str, len_qs_list: int) -> int | None:
    """
    Парсить індекс із request.POST ключа з певним префіксом.
    Якщо індекс виходить за межі phones_qs — повертає None і показує повідомлення.
    """
    if key and key.startswith(prefix):
        try:
            index = int(key.split("_")[-1])
            if index < len_qs_list:
                return index
        except ValueError:
            print("Неправильний формат ключа")
            return None
    return None






def get_companies_with_same_contact(contact_id: int):
    """
    Повертає список компаній, де існує контакт з таким же full_name, 
    як у вказаного контакту, крім контакту з full_name == "Офіс" 
    та окрім поточної компанії за edrpou.
    """
    try:
        contact = ContactPerson.objects.get(id=contact_id)
    except (ContactPerson.DoesNotExist):
        return []

    # Ім'я контактної особи
    name = contact.full_name

    # Всі контакти з таким же full_name, крім "Офіс" і поточного контакту
    matching_contacts = ContactPerson.objects.filter(full_name=name).exclude(full_name="Офіс")

    # Усі компанії, де є ці контакти
    companies = Company.objects.filter(contacts__in=matching_contacts).distinct()

    print(matching_contacts)
    print(companies)
    return list(companies)


def save_phone_to_company(
    request: HttpRequest,
    ph_form: PhoneForm,
    company: Company,
) -> Optional[Phone]:
    """
    Зберігає телефон з форми та прив'язує його до компанії.
    
    :param request: HttpRequest — для повідомлень
    :param ph_form: PhoneForm — форма з даними телефону
    :param company: Company — компанія, до якої прив'язати телефон
    :return: Phone або None
    """
     

    if ph_form.is_valid():
        number: str = ph_form.cleaned_data["number"]
        status: str = ph_form.cleaned_data.get("status", "on")

        if number:
            edrpou: str = company.edrpou
            phone: Optional[Phone] = Phone.objects.filter(number=number).first()
            if phone:
                phone.status = status
                phone.companies.add(company)
                messages.info(request, f"Телефон {number} вже існував, прив'язано до компанії {edrpou}.")
            else:
                phone = Phone.objects.create(number=number, status=status)
                phone.companies.add(company)
                messages.success(request, f"Телефон {number} створено та прив'язано до компанії {edrpou}.")
        else:
            phone = None
            messages.warning(request, "Не вказано номер телефону.")
    else:
        phone = None
        messages.error(request, "Форма містить помилки. Перевірте введені дані.")
    return phone


def save_phone_to_company_and_contact(
    request: HttpRequest,
    ph_form: PhoneForm,
    co_form: ContactForm,
    company: Company
) -> Tuple[Optional[Phone], Optional[ContactPerson]]:
    
    phone = save_phone_to_company(request, ph_form, company)
    contact: Optional[ContactPerson] = None

    if phone:
        if co_form.is_valid():
            name = co_form.cleaned_data["full_name"]
            position = co_form.cleaned_data.get("position", "")

            contact = ContactPerson.objects.filter(full_name=name).first()
            if contact:
                phone.contact = contact
                cont_msg = f"Контакт {name} вже існував, прив'язано до компанії {company.edrpou}."
                messages.info(request, cont_msg)
            else:
                contact = ContactPerson.objects.create(full_name=name, position=position)
                phone.contact = contact
                cont_msg = f"Створено нового контакта {name} та прив'язано до компанії {company.edrpou}."
                messages.success(request, cont_msg)

            # оновлюємо дані (наприклад, посаду)
            contact.position = position
            contact.save()

            # зв'язуємо з компанією
            contact.companies.add(company)

            # зберігаємо телефон з прив'язаним контактом
            phone.save()

        else:
            messages.warning(request, "Форма контакту містить помилки або порожня.")
    else:
        messages.error(request, "Телефон не було збережено, контакт також не створено.")

    return phone, contact








def search_in_queryset(qs: QuerySet, search: str) -> QuerySet:

    """
    Універсальний пошук:
    - працює для будь-якого QuerySet
    - шукає по всіх текстових полях (CharField, TextField)
    - включає зв’язки (ForeignKey, OneToOne, ManyToMany) на 1 рівень глибини
    """

    if not search:
        return qs

    model = qs.model
    q = Q()
    sets = []
    sets.append(_get_fields_name_from_model(model))
    sets.append(_get_fields_name_from_model_one_to_one(model))
    sets.append(_get_fields_name_from_model_m2m(model))
    sets.append(_get_fields_name_from_model_m2m_reverse(model))
    fields = set().union(*sets)
    for field in fields:
        q |= Q(**{f"{field}__icontains": search})
    
    return qs.filter(q).distinct()


def quick_search_companies(search: Optional[str] = None) -> QuerySet[Company]:
    """
    Швидкий пошук компаній тільки по стовпцях моделі Company:
    - edrpou
    - name
    - legal_address
    - hectares (як текст)

    :param search: рядок для пошуку
    :return: QuerySet з компаніями
    """
    qs: QuerySet[Company] = Company.objects.all()

    
    if search:
        qs = Company.objects.annotate(
            last_call=Max("calls__datetime"),
            next_call=Min("planned_calls__planned_datetime", 
                        filter=Q(planned_calls__status="on")  # враховуємо тільки активні плани
                            )
            )
        qs = qs.filter(
            Q(edrpou__icontains=search) |
            Q(name__icontains=search) |
            Q(legal_address__icontains=search) |
            Q(hectares__icontains=search)
        )
        

    return qs



def _get_fields_name_from_model(model: Type[Model]) -> set[str]:

    """ 
    Повертає список текстових полів моделі
    """
    fields: Set[str] = set()
    for field in model._meta.get_fields():
        if isinstance(field, (CharField, TextField)):
            fields.add(field.name)
    return fields


def _get_fields_name_from_model_one_to_one(model: Type[Model]) -> set[str]:

    """ 
    Повертає сет повязаних текстових полів, у яких є звязок
    один до одного через fk з полями моделі
    # ForeignKey / OneToOne
    f"{field.name}__{subfield.name}
    """
    fields: Set[str] = set()
    for field in model._meta.get_fields():
        if isinstance(field, (ForeignKey, OneToOneField)):
            related_model = field.related_model
            for subfield in related_model._meta.get_fields():
                if isinstance(subfield, (CharField, TextField)):
                    fields.add(f"{field.name}__{subfield.name}")
    return fields


def _get_fields_name_from_model_m2m(model: Type[Model]) -> set[str]:
    
    """ 
    Повертає сет повязаних текстових полів, у яких є 
    прямий звязок m2m з полями моделі
    f"{field.name}__{subfield.name}
    """

    fields: Set[str] = set()
    for field in model._meta.get_fields():
        # Прямий ManyToMany
        if isinstance(field, ManyToManyField):
            related_model = field.remote_field.model
            for subfield in related_model._meta.get_fields():
                if isinstance(subfield, (CharField, TextField)):
                    fields.add(f"{field.name}__{subfield.name}")
    return fields


def _get_fields_name_from_model_m2m_reverse(model: Type[Model]) -> set[str]:
    
    """ 
    Повертає сет повязаних текстових полів, у яких є 
    зворотній звязок m2m з полями моделі
    ManyToManyRel
    f"{field.name}__{subfield.name}
    """
    fields: Set[str] = set()
    for field in model._meta.get_fields():
        if isinstance(field, ManyToManyRel):
            related_model = field.related_model
            for subfield in related_model._meta.get_fields():
                if isinstance(subfield, (CharField, TextField)):
                    fields.add(f"{field.get_accessor_name()}__{subfield.name}")
    return fields


def get_company_by_edrpou(edrpou: str, qs: QuerySet[Company] | None = None) -> Company | None:
    """
    Повертає Company за edrpou або None, якщо компанія не знайдена.
    Можна передати готовий QuerySet (наприклад, відфільтрований або кешований).
    """
    if not edrpou:
        return None

    if qs is None:
        qs = Company.objects.all()

    return qs.filter(edrpou=edrpou).first()

def get_company_calls_by_edrpou(
    edrpou: str,
    company_qs: QuerySet[Company] | None = None
) -> QuerySet[Call] | None:
    """
    Повертає QuerySet дзвінків для компанії з заданим edrpou.
    Можна передати готовий QuerySet компаній.
    Якщо компанія не знайдена, повертає None.
    """
    company = get_company_by_edrpou(edrpou, qs=company_qs)
    if company is None:
        return None
    return Call.objects.filter(company=company).order_by('-datetime')


def _filter_by_hectares(qs: QuerySet, hectares_val: str | int, hectares_op: str | None = None) -> QuerySet:
    """
    Фільтрує QuerySet компаній за полем hectares.
    
    :param qs: QuerySet, який фільтруємо
    :param hectares_val: значення для порівняння (рядок або int)
    :param hectares_op: оператор порівняння: ">", "<", ">=", "<=", None
    :return: відфільтрований QuerySet
    """
    if not hectares_val:
        return qs
    
    try:
        val = int(hectares_val)
    except (ValueError, TypeError):
        return qs  # якщо не число, повертаємо без змін

    if hectares_op in (">", "<", ">=", "<="):
        lookup = {
            ">": "hectares__gt",
            "<": "hectares__lt",
            ">=": "hectares__gte",
            "<=": "hectares__lte",
        }[hectares_op]
        return qs.filter(**{lookup: val})
    
    return qs.filter(hectares=val)


def _sort_queryset(qs: QuerySet, sort_field: str, direction: str = "asc", allowed_fields: List[str] = None) -> QuerySet:
    """
    Сортування QuerySet за заданим полем.
    
    :param qs: QuerySet для сортування
    :param sort_field: поле для сортування
    :param direction: напрямок сортування: "asc" або "desc"
    :param allowed_fields: список дозволених полів для сортування
    :return: відсортований QuerySet
    """
    if allowed_fields is None:
        allowed_fields = []
    
    if sort_field in allowed_fields:
        order = sort_field if direction == "asc" else f"-{sort_field}"
        qs = qs.order_by(order)
    return qs


def _sort_key(c, sort):
    value = getattr(c, sort)

    if sort in ["last_call"]:
        return value or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    elif sort in ["next_call"]:
        return value or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
    elif sort in ["hectares"]:
        return value if value is not None else -1  # або 0, залежно від логіки
    else:
        return value