from typing import Dict, Any
from itertools import chain

from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.db.models import Sum, Prefetch
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.http import HttpRequest, HttpResponse
from django.contrib import messages

from .models import Company, ContactPerson, Phone, Call, Holding, CallPlan, Warehouse, StockItem
from .forms import CompanyForm, ContactForm, PhoneForm, HoldingForm, CallForm, PlanCallForm
from .checkers import check_phone
from .utils import *
from .views_utils import *


def mainpage(request):
    return render(request, "calling_app/base.html")


def homepage(request):
    return render(request, "calling_app/home.html")


def company_page(request: HttpRequest, edrpou: str) -> HttpResponse:
    """
    Відображає сторінку компанії з усією інформацією: контакти, телефони, дзвінки,
    склади, товари на складі та інформацію про холдинг.

    Оптимізовано через `prefetch_related` для мінімізації кількості запитів до БД.

    Args:
        request (HttpRequest): HTTP-запит.
        edrpou (str): ЄДРПОУ компанії для ідентифікації.

    Returns:
        HttpResponse: Відрендерений шаблон "company_page.html" з контекстом.
    
    Context:
        company (Company): Об'єкт компанії.
        holding (Holding | None): Холдинг компанії, якщо є.
        holding_hectares (float): Сумарна площа всіх компаній холдингу.
        contacts (QuerySet[ContactPerson]): Контакти компанії.
        contact_phones (dict): Словник контакт → список телефонів з останнім дзвінком та кількістю дзвінків.
        phones_without_contact (list): Список телефонів компанії, що не прив'язані до контактів.
        calls (list[Call]): Усі дзвінки по компанії, відсортовані за датою (новіші спершу).
        count_calls (int): Кількість дзвінків по компанії.
        planned_calls (QuerySet[Call]): Планові дзвінки компанії.
        warehouses (QuerySet[Warehouse]): Склади компанії.
        stock_items (QuerySet[StockItem]): Товари компанії.
        edit_contact_url (str): Ідентифікатор URL для редагування контакту.
        for_company (bool): Позначка, що контекст для сторінки компанії.
    """

    # Оптимізуємо запити: підвантажуємо контакти, телефони та дзвінки
    company = get_object_or_404(
        Company.objects.prefetch_related(
            Prefetch("contacts__phones__calls"),
            Prefetch("phones__calls"),
            "planned_calls",
            "owned_warehouses",
            "stock_items",
        ),
        edrpou=edrpou
    )

    holding = company.holding
    holding_hectares = 0
    if holding:
        holding_hectares = holding.companies.aggregate(total=Sum("hectares"))["total"] or 0

    contacts = company.contacts.all()

    # Контакти з телефонами
    contact_phones = {
        contact: [
            {
                "phone": phone,
                "last_call": max(phone.calls.all(), key=lambda c: c.datetime, default=None),
                "count_calls": phone.calls.count(),
            }
            for phone in contact.phones.filter(companies=company)
        ]
        for contact in contacts
    }

    # Телефони, що вже закріплені за контактами
    phones_in_contacts_ids = [
        phone_data["phone"].id
        for phones in contact_phones.values()
        for phone_data in phones
    ]

    # Телефони без контакту
    phones_without_contact_qs = company.phones.exclude(id__in=phones_in_contacts_ids)
    phones_without_contact = [
        {
            "phone": phone,
            "last_call": max(phone.calls.all(), key=lambda c: c.datetime, default=None),
            "count_calls": phone.calls.count(),
        }
        for phone in phones_without_contact_qs
    ]

    # Усі дзвінки по компанії (телефони, включаючи prefetch)
    calls = Call.objects.filter(phone__companies=company).order_by("-datetime")[:5]
    count_calls = len(calls)

    emails = company.emails.all()

    context: Dict[str, Any] = {
        "company": company,
        "holding": holding,
        "holding_hectares": holding_hectares,
        "contacts": contacts,
        "emails": emails,
        "contact_phones": contact_phones,
        "calls": calls,
        "count_calls": count_calls,
        "planned_calls": company.planned_calls.all(),
        "next_plan": company.planned_calls.filter(status="on").order_by("planned_datetime").first(),
        "warehouses": company.owned_warehouses.all(),
        "stock_items": company.stock_items.all(),
        "phones_without_contact": phones_without_contact,
        "edit_contact_url": "edit_contact",
        "for_company": True,
    }

    # Обробка POST для кнопок додавання контакту або холдингу
    if request.method == "POST":
        if "add_contact" in request.POST:
            return redirect("add_contact", edrpou=company.edrpou)
        if "add_holding" in request.POST:
            return redirect("add_holding", edrpou=company.edrpou)

    return render(request, "calling_app/company_page.html", context)


def companies(request):
    context = get_filtered_sorted_companies_context(request)
    return render(request, "calling_app/companies.html", context)


def add_company_to_holding(request, holding_id):
    context = get_filtered_sorted_companies_context(request)

    holding = get_object_or_404(Holding, id=holding_id)
    context["add_company_to_holding"] = True
    context["holding_id"] = holding_id
    context["holding"] = holding  

    if request.method == "POST":
        selected_edrpou = request.POST.get("selected_company")
        if selected_edrpou:
            company = Company.objects.get(edrpou=selected_edrpou)
            company.holding = holding
            company.save()
            context["msg"] = f"✅ Компанію {company.name} додано до холдингу {holding.name}"

    return render(request, "calling_app/companies.html", context)


class CompanyCreate(CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'calling_app/create_company.html'
    success_url = reverse_lazy('companies')  # змінити на свій URL
    def post(self, request, *args, **kwargs):
        # Тут request доступний
        print("POST data:", request.POST)
        return super().post(request, *args, **kwargs)
    def get_success_url(self):
        # self.object — це щойно створений об'єкт
        return reverse('company_page', kwargs={'edrpou': self.object.edrpou})


class CompanyUpdate(UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'calling_app/create_company.html'
    slug_field = "edrpou"
    slug_url_kwarg = "edrpou"

    def get_success_url(self):
        # Повертаємося на ту ж сторінку компанії
        return reverse('update_company', kwargs={'edrpou': self.object.edrpou})


class ContactCreate(CreateView):
    model = ContactPerson
    form_class = ContactForm
    template_name = 'calling_app/edit_contact.html'
    def post(self, request, *args, **kwargs):
        # Тут request доступний
        print("POST data:", request.POST)
        return super().post(request, *args, **kwargs)
    def get_success_url(self):
        # self.object — це щойно створений об'єкт
        return reverse('companies')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # тепер форма буде доступна і як form, і як co_form
        context["co_form"] = context["form"]
        return context
    

def add_contact(request: HttpRequest, edrpou: str) -> HttpResponse:
    """
    Додає нову контактну особу до компанії або прив'язує існуючу.
    Відображає форму для створення/редагування контакту.
    """
    company = get_object_or_404(Company, edrpou=edrpou)
    message = None

    if request.method == "POST":
        co_form = ContactForm(request.POST, prefix="contact")
        if "save_contact" in request.POST:
            contact, message = get_or_create_contact_in_company(co_form, company)
            messages.info(request, message)
            return redirect("edit_contact", edrpou=company.edrpou, id_contact=contact.id) # Редірект на сторінку редагування контакту
    else:
        co_form = ContactForm(prefix="contact")
    ph_forms = [PhoneForm(prefix="phone-0")] # Для нового контакту створюємо порожню форму телефону
    context = {
        "company": company,
        "co_form": co_form,
        "ph_forms": ph_forms,
    }
    return render(request, "calling_app/edit_contact.html", context)


def edit_contact(request, edrpou, id_contact=1):
    company, contact = get_company_contact(edrpou, id_contact)

    phones_qs = list(Phone.objects.filter(contact=contact, companies=company))  # Існуючі телефони цього контакту та компанії
    phones_qs.append(Phone(number=None, status="on", contact=contact)) # додаємо пустий телефон для пустої форми до списку

    co_form = ContactForm(instance=contact, prefix="contact")
    ph_forms = [PhoneForm(instance=phone, prefix=f"phone-{i}") for i, phone in enumerate(phones_qs)]

    contact_companies = get_companies_with_same_contact(id_contact)
    message = None

    if request.method == "POST":
        print("POST")
        co_form = ContactForm(request.POST, instance=contact, prefix="contact")
        pressed_update_ph = next((k for k in request.POST if k.startswith("update_phone_")), None)
        pressed_dell_ph = next((k for k in request.POST if k.startswith("dell_phone_from_contact_")), None)
        print(pressed_dell_ph)

        len_phone_qs = len(phones_qs)
        
        pressed_update_index = get_index_from_post(pressed_update_ph, "update_phone_", len_phone_qs)
        pressed_dell_index = get_index_from_post(pressed_dell_ph, "dell_phone_from_contact_", len_phone_qs)
        print(pressed_dell_index)


        if "save_contact" in request.POST:
            message = save_contact_with_form(co_form)

        elif "dell_contact_from_company" in request.POST:
            message = delete_contact_from_company(contact, company)

        elif pressed_update_index is not None:
            phone = phones_qs[pressed_update_index]
            ph_form = PhoneForm(request.POST, instance=phone, prefix=f"phone-{pressed_update_index}")
            ph_forms, message = update_phone_in_company_contact_by_index(ph_form, 
                                                                            contact, 
                                                                            company, 
                                                                            ph_forms, 
                                                                            pressed_update_index)
            messages.info(request, message)

        elif pressed_dell_index is not None:
            phone = phones_qs[pressed_dell_index]
            if phone.number:
                cp_contact = check_point(request, f"contact_{pressed_dell_index}")
                cp_company =  check_point(request, f"company_{pressed_dell_index}")

                message = delete_phone_from_contact_company(contact, 
                                                            cp_contact, 
                                                            cp_company,
                                                            company,
                                                            phones_qs,
                                                            pressed_dell_index)
                messages.info(request, message)

        return redirect(request.path)

    phones = Phone.objects.filter(contact=contact, companies=company).prefetch_related("calls")
    calls = [call for phone in phones for call in phone.calls.all()]
    messages.info(request, message)


    context = {
        "company": company,
        "contact": contact,
        "ph_forms": ph_forms,
        "co_form": co_form,
        "contact_companies": contact_companies,
        "calls": calls,
        "count_calls": len(calls),
        "phones": phones_qs,
        "for_contact": True,
    }

    return render(request, "calling_app/edit_contact.html", context=context)


def add_holding(request, edrpou):
    context = get_or_create_holding_company(request, edrpou)
    if context["redirect"]: 
        return context["redirect"]
    return render(request, "calling_app/add_holding.html", context)


def edit_holding(request, edrpou, holding_id):
    context = get_or_create_holding_company(request, edrpou)
    if context["redirect"]: 
        return context["redirect"]
    
    holding = get_object_or_404(Holding, id=holding_id)
    companies = Company.objects.filter(holding_id=holding_id)
    holding_hectares = holding.companies.aggregate(total=Sum("hectares"))["total"] or 0
    company = context["company"]

    cont_msg = context["cont_msg"]
    co_form = HoldingForm(prefix="name", instance=holding)

    if request.method == "POST":
        co_form = HoldingForm(request.POST, prefix="name")
        if "add_company_to_holding" in request.POST:
            return redirect("add_company_to_holding", holding_id=holding_id)
        if "dell_company" in request.POST:
            if co_form.is_valid():
                name = co_form.cleaned_data["name"]
                holding, created = Holding.objects.get_or_create(name=name)
                company.holding = None
                company.save()
                holding_id = holding.id
                if created:
                    cont_msg = f"✅ Створено новий холдинг: {holding.name}"
                else:
                    cont_msg = f"🔄 Компанію {company.name} видалено з холдингу {holding.name}"
                
            else:
                cont_msg = "❌ Форма невірна. Перевірте введені дані."

            return redirect("edit_holding", edrpou=edrpou, holding_id=holding_id)

    context["company"] = company
    context["co_form"] = co_form
    context["cont_msg"] = cont_msg
    context["companies"] = companies
    context["holding_hectares"] = holding_hectares # кількість гектар поточного холдингу
    
    return render(request, "calling_app/add_holding.html", context)


def add_phone(request, edrpou):
    company = get_object_or_404(Company, edrpou=edrpou)

    if request.method == "POST":
        co_form = ContactForm(request.POST, prefix="contact")
        ph_form = PhoneForm(request.POST, prefix="phone")
        if "save_phone" in request.POST:
           phone = save_phone_to_company(request=request, ph_form=ph_form, company=company)
           if phone:
                return redirect("edit_phone", edrpou=company.edrpou, id_phone=phone.id)
    else:
        ph_form = PhoneForm(prefix="phone")
        co_form = ContactForm(prefix="contact")

    context = {
        "company": company,
        "ph_form": ph_form,
        "co_form": co_form,
    }
    return render(request, "calling_app/phone.html", context)


def edit_phone(request, edrpou, id_phone):
    company = get_object_or_404(Company, edrpou=edrpou)
    phone = get_object_or_404(Phone, id=id_phone)
    ph_form = PhoneForm(request.POST or None, prefix="phone", instance=phone)
    contact = getattr(phone, "contact", None)
    co_form = ContactForm(request.POST, instance=contact)

    if not contact:
        contact = get_object_or_404(ContactPerson, id=1)
        
    co_form = ContactForm(request.POST or None, prefix="contact", instance=contact)

    if request.method == "POST":
        co_form = ContactForm(request.POST, prefix="contact")
        ph_form = PhoneForm(request.POST, prefix="phone")
        if "save_phone" in request.POST:
            phone, contact = save_phone_to_company_and_contact(request=request, 
                                                               ph_form=ph_form,
                                                               co_form=co_form, 
                                                               company=company)
            if phone:
                return redirect("edit_phone", edrpou=company.edrpou, id_phone=phone.id)
        if "dell_phone_from_company" in request.POST:
            phone.companies.remove(company)
            return redirect("company_page", edrpou=company.edrpou)

    calls = [c for c in phone.calls.all()]
    count_calls = len(calls)

    related_companies = (phone.companies.exclude(phones__number="+380000000000"))

    context = {
        "company": company,
        "ph_form": ph_form,
        "co_form": co_form,
        "contact": contact,
        "calls": calls,
        "count_calls": count_calls,
        "phone": phone,
        "related_companies": related_companies,
        "for_phone": True,
    }
    return render(request, "calling_app/phone.html", context)


def add_call(request, edrpou, id_phone):
    company = get_object_or_404(Company, edrpou=edrpou)
    phone = get_object_or_404(Phone, id=id_phone)

    related_companies = phone.companies.exclude(phones__number="+380000000000")

    if request.method == "POST":
        form = CallForm(request.POST, company=company, phone=phone)
        if form.is_valid():
            call = form.save()
            messages.success(request, f"✅ Дзвінок до {phone.number} збережено.")
            return redirect("edit_call", call.id)
        else:
            messages.error(request, "❌ Сталася помилка при збереженні дзвінка.")
    else:
        form = CallForm(company=company, phone=phone)
    
    calls = list(phone.calls.order_by("-datetime"))
    count_calls = len(calls)

    context = {
        "company": company,
        "phone": phone,
        "form": form,
        "related_companies": related_companies,
        "calls": calls,
        "count_calls": count_calls,
        "for_phone": True,
    }
    return render(request, "calling_app/call.html", context)


def edit_call(request, id_call):
    call = get_object_or_404(Call, id=id_call)
    phone = call.phone
    company_list = list(call.company.all())

    if request.method == "POST":
        form = CallForm(request.POST, instance=call, company=None, phone=None)
        if form.is_valid():
            form.save()
            messages.success(request, f"✅ Дзвінок до {phone.number} успішно оновлено.")
            return redirect("edit_call", call.id)
        else:
            messages.error(request, "❌ Сталася помилка при оновленні дзвінка.")
    else:
        form = CallForm(instance=call, company=None, phone=None)

    context = {
        "form": form,
        "call": call,
        "phone": phone,
        "company": company_list[0] if company_list else None,  # перша компанія
        "related_companies": call.company.exclude(phones__number="+380000000000"),
        "calls": list(phone.calls.order_by("-datetime")),
        "count_calls": phone.calls.count(),
        "for_phone": True,
    }
    return render(request, "calling_app/call.html", context)


def calls_of_company(request: HttpRequest, edrpou: str) -> HttpResponse:
    """
    Відображає всі дзвінки конкретної компанії.
    """
    company = get_object_or_404(Company, edrpou=edrpou)
    next_plan = company.planned_calls.filter(status="on").order_by("planned_datetime").first()

    # Всі дзвінки компанії (по всіх телефонах ManyToMany)
    calls_qs = (
        Call.objects
        .filter(phone__companies=company)
        .select_related("phone")     # щоб не робити зайвих запитів
        .order_by("-datetime")
    )

    context = {
        "next_plan": next_plan,
        "company": company,
        "calls": calls_qs,
        "count_calls": calls_qs.count(),
    }
    return render(request, "calling_app/calls_of_company.html", context)


def add_plan_call(request, edrpou, id_phone=None, id_call=None):
    company = get_object_or_404(Company, edrpou=edrpou)
    phone = None
    call = None

    if id_phone:
        phone = get_object_or_404(Phone, id=id_phone)
    if id_call:
        call = get_object_or_404(Call, id=id_call)
        phone = call.phone  # щоб мати консистентність

    if request.method == "POST":
        form = PlanCallForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.company = company
            plan.phone = phone
            plan.call = call
            plan.save()
            messages.success(request, "✅ План дзвінка збережено")
            return redirect("edit_plan_call", id_plan_call=plan.id)
        else:
            messages.error(request, "❌ Помилка при створенні плану")
    else:
        form = PlanCallForm()

    return render(request, "calling_app/plan_call.html", {
        "form": form,
        "company": company,
        "phone": phone,
        "call": call,
    })


def edit_plan_call(request, id_plan_call):
    plan_call = get_object_or_404(CallPlan, id=id_plan_call)
    company = plan_call.company
    phone = plan_call.phone
    call = plan_call.call

    if request.method == "POST":
        form = PlanCallForm(request.POST, instance=plan_call)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ План дзвінка збережено")
            return redirect("edit_plan_call", id_plan_call=plan_call.id)  # краще ніж request.path
        else:
            messages.error(request, "❌ Помилка при створенні плану")
    else:
        form = PlanCallForm(instance=plan_call)

    return render(request, "calling_app/plan_call.html", {
        "form": form,
        "company": company,
        "phone": phone,
        "call": call,
    })


def show_all_company_links(request, edrpou: str):
    company = get_object_or_404(Company, edrpou=edrpou)

    # Холдинг
    holding_links = []
    if company.holding:
        for c in company.holding.companies.exclude(id=company.id):
            holding_links.append({
                "edrpou": c.edrpou,
                "name": c.name,
                "hectares": c.hectares,
                "address": c.legal_address
            })

    # Зв'язки по номерах телефонів (крім конкретного номера)
    phone_links = []
    for phone in company.phones.exclude(number="+380000000000"):
        linked_companies = phone.companies.exclude(id=company.id)
        linked_data = [{
            "edrpou": c.edrpou,
            "name": c.name,
            "hectares": c.hectares,
            "address": c.legal_address
        } for c in linked_companies]
        if linked_data:
            phone_links.append({
                "number": phone.number,
                "companies": linked_data
            })

    # Зв'язки по ПІБ контактів (мінімум 3 частини)
    contact_links = []
    for contact in company.contacts.all():
        if len(contact.full_name.split()) >= 3:
            linked_companies = contact.companies.exclude(id=company.id)
            linked_data = [{
                "edrpou": c.edrpou,
                "name": c.name,
                "hectares": c.hectares,
                "address": c.legal_address
            } for c in linked_companies]
            if linked_data:
                contact_links.append({
                    "full_name": contact.full_name,
                    "companies": linked_data
                })

    # Зв'язки по адресі
    address_links = Company.objects.filter(legal_address=company.legal_address).exclude(id=company.id) if company.legal_address else []

    # Зв'язки по email
    email_links = []
    for email in company.emails.all():
        linked_companies = email.companies.exclude(id=company.id)
        if linked_companies.exists():
            email_links.append({
                "email": email.email,
                "companies": linked_companies
            })

    # ====== Усі пов’язані компанії ======
    all_related = {}  # ключ: edrpou, значення: {"company": {...}, "types": set()}
    
    # Додати холдинг
    for c in holding_links:
        all_related.setdefault(c["edrpou"], {"company": c, "types": set()})
        all_related[c["edrpou"]]["types"].add("Холдинг")
    
    # Додати телефонні зв’язки
    for ph in phone_links:
        for c in ph["companies"]:
            all_related.setdefault(c["edrpou"], {"company": c, "types": set()})
            all_related[c["edrpou"]]["types"].add("Телефон")
    
    # Додати контактні зв’язки
    for ct in contact_links:
        for c in ct["companies"]:
            all_related.setdefault(c["edrpou"], {"company": c, "types": set()})
            all_related[c["edrpou"]]["types"].add("Контакт")
    
    # Додати адресні зв’язки
    for c in address_links:
        c_dict = {"edrpou": c.edrpou, "name": c.name, "hectares": c.hectares, "address": c.legal_address}
        all_related.setdefault(c.edrpou, {"company": c_dict, "types": set()})
        all_related[c.edrpou]["types"].add("Адреса")
    
    # Додати email зв’язки
    for em in email_links:
        for c in em["companies"]:
            all_related.setdefault(c.edrpou, {"company": c, "types": set()})
            all_related[c.edrpou]["types"].add("Email")

    # Привести до списку для шаблону
    all_related_companies = [
        {"company": data["company"], "types": ", ".join(sorted(data["types"]))}
        for data in all_related.values()
    ]

    context = {
        "company": company,
        "holding": company.holding,
        "holding_links": holding_links,
        "phone_links": phone_links,
        "contact_links": contact_links,
        "address_links": address_links,
        "email_links": email_links,
        "all_related_companies": all_related_companies,
    }

    return render(request, "calling_app/show_all_company_links.html", context)





