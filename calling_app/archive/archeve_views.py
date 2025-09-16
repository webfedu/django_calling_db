from django.shortcuts import render, redirect, get_object_or_404
from ..forms import CompanyForm, ContactForm, PhoneForm
from ..models import District, Company, Region, ContactPerson, Phone
from ..checkers import check_edrpou, check_area, check_phone, check_person


def mainpage(request):
    """
    Відображає головну сторінку з хедером та меню
    """
    return render(request, "calling_app/base.html")


def homepage(request):
    """
    Відображає головну сторінку з хедером та меню
    """
    return render(request, "calling_app/home.html")


def set_company(edrpou, name, address, region_id, district_id, area):
    edrpou = check_edrpou(edrpou)
    area = check_area(area)
    
    company, created = Company.objects.update_or_create(
    edrpou=edrpou,
    defaults={
        "name": name,
        "legal_address": address,
        "region_id": region_id,
        "district_id": district_id,
        "hectares": area,
    })

    return company


def set_phone(number, edrpou, contact_id, status):
    edrpou = check_edrpou(edrpou)
    number = check_phone(number)

    # отримуємо компанію по коду ЄДРПОУ
    company = get_object_or_404(Company, edrpou=edrpou)

    phone, created = Phone.objects.update_or_create(
        number=number,
        contact_id=contact_id,
        company=company,   # ← додаємо зв’язок із компанією
        defaults={
            "number": number,
            "status": status
        }
    )

    return phone


def set_contact(edrpou, full_name, position):
    edrpou = check_edrpou(edrpou)
    company = get_object_or_404(Company, edrpou=edrpou)
    full_name = check_person

    contact, created = ContactPerson.objects.update_or_create(
        full_name=full_name,
        position=position,
        companies=company,   # ← додаємо зв’язок із компанією
        defaults={
            "full_name": full_name,
            "position": position,
        }
    )

    return contact


def company_page(request, edrpou):
    # Отримуємо компанію або 404
    company = get_object_or_404(Company, edrpou=edrpou)

    # Холдинг
    holding = company.holding

    # Контакти та телефони
    contacts = company.contacts.all()  # ContactPerson
    contact_phones = {c.id: c.phones.all() for c in contacts}  # словник: contact.id -> телефони

    # Дзвінки
    calls = company.calls.all()  # пов’язані дзвінки
    planned_calls = company.planned_calls.all()  # плановані дзвінки

    # Склади / Warehouse
    warehouses = company.warehouses.all()

    # Залишки / StockItem
    stock_items = company.stock_items.all()

    context = {
        "company": company,
        "holding": holding,
        "contacts": contacts,
        "contact_phones": contact_phones,
        "calls": calls,
        "planned_calls": planned_calls,
        "warehouses": warehouses,
        "stock_items": stock_items,
    }

    return render(request, "calling_app/company_page.html", context)


    company = get_object_or_404(Company, edrpou=edrpou)

    if request.method == "POST":
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            return redirect('company_page', edrpou=company.edrpou)
    else:
        form = CompanyForm(instance=company)

    # Обов'язково повертаємо render
    return render(request, "calling_app/add_company.html", {"form": form, "company": company})


def add_or_edit_company(request, edrpou=None):
    message = ''
    company = get_object_or_404(Company, edrpou=edrpou) if edrpou else None
    if company:
        message = f"Компанія з ЕДРПОУ {edrpou} вже існує. Внести зміни?"

    if request.method == "POST":
        form = CompanyForm(request.POST, instance=company)
        edrpou_post = check_edrpou(request.POST.get("edrpou"))
        name = request.POST.get("name")
        legal_address = request.POST.get("legal_address")
        region_id = request.POST.get("region")
        district_id = request.POST.get("district")
        hectares = check_area(request.POST.get("hectares"))

        # Перевірка наявності іншої компанії з таким ЕДРПОУ
        exists = Company.objects.filter(edrpou=edrpou_post).exclude(pk=company.pk if company else None).exists()

        if exists:
            # Якщо існує дубль, але користувач ще не підтвердив дію
            if "update" in request.POST:
                company = set_company(edrpou_post, name, legal_address, region_id, district_id, hectares)
                return redirect("home")
            elif "cancel" in request.POST:
                return redirect("home")
            elif "lookat" in request.POST:
                return redirect("company_page", edrpou=edrpou_post)
            else:
                # залишаємо форму з введеними даними
                form = CompanyForm(request.POST, instance=company)
            message = f"Компанія з ЕДРПОУ {edrpou_post} вже існує. Внести зміни?"
        else:
            # Якщо дубля немає
            if form.is_valid():
                company = set_company(edrpou_post, name, legal_address, region_id, district_id, hectares)
                return redirect("home")
            else:
                message = "Форма невалідна"

    else:
        # GET-запит — заповнюємо форму для редагування або порожню для нової компанії
        form = CompanyForm(instance=company)

    return render(
        request,
        "calling_app/add_company.html",
        {
            "form": form,
            "message": message,
            "company": company
        }
    )




def edit_contact(request, company_edrpou, contact_id=None):
    company = get_object_or_404(Company, edrpou=company_edrpou)  # ← отримали компанію
    contact = get_object_or_404(ContactPerson, id=contact_id, companies=company) if contact_id else None
    
    cform = ContactForm(request.POST or None, instance=contact)

    formlist = []
    if contact:
        phones = contact.phones.all()
        for phone in phones:
            formlist.append(PhoneForm(request.POST or None, instance=phone))
    # форма для нового телефону
    formlist.append(PhoneForm(request.POST or None))

    if request.method == "POST":
        exists = ContactPerson.objects.filter(contact_id=contact_id).exclude(pk=contact.pk if contact else None).exists()
        
        if exists:
            contact = set_contact()
            # зберігаємо телефони і прив’язуємо до контакта та компанії
            for f in formlist:
                phone = f.save(commit=False)
                if phone.number:  # уникаємо пустих телефонів
                    phone.contact = contact
                    phone.companies = company
                    phone.save()
        else:
        # Якщо дубля немає
            if cform.is_valid():
                contact = set_contact()
                return redirect("company_page", company_edrpou)
            else:
                message = "Форма контакут невалідна"
            return redirect("company_page", company_edrpou)  # або куди потрібно

    context = {
        "cform": cform,
        "formlist": formlist,
        "company": company,
    }
    return render(request, "calling_app/edit_contact.html", context)


# if search:
    #     q = Q(name__icontains=search) | Q(edrpou__icontains=search) | Q(legal_address__icontains=search)
    #     q |= Q(contacts__full_name__icontains=search) | Q(contacts__position__icontains=search)
    #     q |= Q(phones__number__icontains=search) | Q(phones__status__icontains=search)
    #     q |= Q(emails__email__icontains=search)
    #     q |= Q(owned_warehouses__capacity_tons__icontains=search) | Q(owned_warehouses__transport_type__icontains=search)
    #     q |= Q(used_warehouses__capacity_tons__icontains=search) | Q(used_warehouses__transport_type__icontains=search)
    #     q |= Q(stock_items__crop__name__icontains=search) | Q(stock_items__quantity__icontains=search)
    #     qs = qs.filter(q).distinct()