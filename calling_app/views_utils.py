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


def get_filtered_sorted_companies_context(request):
    qs = get_filtered_sorted_companies(
        _company_headers,
        search=request.GET.get("search", "").strip(),
        hectares_val=request.GET.get("hectares_val"),
        hectares_op=request.GET.get("hectares_op"),
        sort=request.GET.get("sort", "edrpou"),
        direction=request.GET.get("direction", "asc"),
    )

    

    paginator = Paginator(qs, int(request.GET.get("per_page", 20)))
    page_obj = paginator.get_page(request.GET.get("page"))

    sort_params = request.GET.copy()
    sort_params.pop("sort", None)
    sort_params.pop("direction", None)
    sort_querystring = sort_params.urlencode()

    page_params = request.GET.copy()
    page_params.pop("page", None)
    page_querystring = page_params.urlencode()

    # Копія GET-параметрів без show_calls
    show_calls_params = request.GET.copy()
    if "show_calls" in show_calls_params:
        del show_calls_params["show_calls"]  # видаляє всі show_calls
    show_calls_querystring = show_calls_params.urlencode()

    context = {
        "companies": page_obj,
        "per_page": int(request.GET.get("per_page", 20)),
        "search": request.GET.get("search", "").strip(),
        "total_count": qs.count(),
        "hectares_op": request.GET.get("hectares_op"),
        "hectares_val": request.GET.get("hectares_val"),
        "sort": request.GET.get("sort", "edrpou"),
        "direction": request.GET.get("direction", "asc"),
        "sort_querystring": sort_querystring,
        "page_querystring": page_querystring,
        "show_calls_querystring": show_calls_querystring,
        "columns": _company_context_columns,
        "selected_company": get_company_by_edrpou(request.GET.get("show_calls")),
        "calls": get_company_calls_by_edrpou(request.GET.get("show_calls")),
    }
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

