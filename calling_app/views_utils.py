from .utils import get_filtered_sorted_companies, get_company_by_edrpou, get_company_calls_by_edrpou
from django.core.paginator import Paginator

from django.db.models import Sum
from .models import ContactPerson, Company, Holding
from typing import Tuple
from .forms import ContactForm, HoldingForm
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect



_company_context_columns = [
            {"field": "edrpou", "label": "ЄДРПОУ"},
            {"field": "name", "label": "Назва"},
            {"field": "legal_address", "label": "Юридична адреса"},
            {"field": "hectares", "label": "Гектари"},
            {"field": "next_call", "label": "Наступний дзвінок"},
            {"field": "last_call", "label": "Останній дзвінок"},
        ]

_company_headers = [col["field"] for col in _company_context_columns]


import time

def get_filtered_sorted_companies_context(request):
    timers = {}

    # 1️⃣ get_filtered_sorted_companies
    start = time.time()
    qs, qs_list = get_filtered_sorted_companies(
        _company_headers,
        search=request.GET.get("search", "").strip(),
        fast_search = request.GET.get("fast_search"),
        hectares_max=request.GET.get("hectares_max"),
        hectares_min=request.GET.get("hectares_min"),
        sort=request.GET.get("sort", "edrpou"),
        direction=request.GET.get("direction", "asc"),
    )
    timers['get_filtered_sorted_companies'] = time.time() - start


    # 3️⃣ Paginator
    start = time.time()
    paginator = Paginator(qs_list, int(request.GET.get("per_page", 20)))
    page_obj = paginator.get_page(request.GET.get("page"))
    timers['Paginator.get_page'] = time.time() - start

    # 4️⃣ Формування querystring
    start = time.time()
    sort_params = request.GET.copy()
    sort_params.pop("sort", None)
    sort_params.pop("direction", None)
    sort_querystring = sort_params.urlencode()

    page_params = request.GET.copy()
    page_params.pop("page", None)
    page_querystring = page_params.urlencode()

    show_calls_params = request.GET.copy()
    if "show_calls" in show_calls_params:
        del show_calls_params["show_calls"]
    show_calls_querystring = show_calls_params.urlencode()
    timers['querystring_processing'] = time.time() - start

    # 5️⃣ get_company_by_edrpou і get_company_calls_by_edrpou
    start = time.time()
    selected_company = get_company_by_edrpou(request.GET.get("show_calls"), qs)
    calls = get_company_calls_by_edrpou(request.GET.get("show_calls"), qs)
    timers['company_calls_lookup'] = time.time() - start

    # 6️⃣ Формування контексту
    start = time.time()
    context = {
        "companies": page_obj,
        "per_page": int(request.GET.get("per_page", 20)),
        "search": request.GET.get("search", "").strip(),
        "total_count": len(qs_list),
        "hectares_min": request.GET.get("hectares_min"),
        "hectares_max": request.GET.get("hectares_max"),
        "sort": request.GET.get("sort", "edrpou"),
        "direction": request.GET.get("direction", "asc"),
        "sort_querystring": sort_querystring,
        "page_querystring": page_querystring,
        "show_calls_querystring": show_calls_querystring,
        "columns": _company_context_columns,
        "selected_company": selected_company,
        "calls": calls,
    }
    timers['context_build'] = time.time() - start

    # 7️⃣ Друк таймерів
    print("=== Timers (seconds) ===")
    for k, v in timers.items():
        print(f"{k}: {v:.4f}")

    return context


def get_or_create_holding_company(request, edrpou):
    company = get_object_or_404(Company, edrpou=edrpou)
    holdings = Holding.objects.annotate(total_hectares=Sum("companies__hectares"))

    holdings_ha = {h.name: h.total_hectares or 0 for h in holdings}
   
    cont_msg = ''
    redir = None

    if request.method == "POST":
        co_form = HoldingForm(request.POST, prefix="name")
        if "save_contact" in request.POST:
            if co_form.is_valid():
                name = co_form.cleaned_data["name"]
                holding = Holding.objects.get_or_create(name=name)[0]
                company.holding = holding
                company.save()
            else:
                cont_msg = "Форма невірна"

            redir = redirect("edit_holding", edrpou=edrpou, holding_id=holding.id)


    else:
        co_form = HoldingForm(prefix="name")

    context = {
        "redirect": redir,
        "company": company,
        "co_form": co_form,
        "cont_msg": cont_msg,
        "holdings_ha": holdings_ha,
        "for_holding": True,
    }
    return context



def check_point(request: HttpRequest, name: str) -> bool:
    if request.POST.get(name) == "on":
        return True

