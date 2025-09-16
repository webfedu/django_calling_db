from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required

from calling_app import views

urlpatterns = [
    path("admin/", admin.site.urls),

    # авторизація
    path('login/', auth_views.LoginView.as_view(template_name='calling_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),

    # Головні сторінки
    path("", login_required(views.mainpage), name="main"),  
    path("home/", login_required(views.homepage), name="home"),  

    # Компанії
    path("companies/", login_required(views.companies), name="companies"),  
    path("company/<str:edrpou>/", login_required(views.company_page), name="company_page"),
    path("create-company/", login_required(views.CompanyCreate.as_view()), name="create_company"),
    path("update-company/<str:edrpou>/", login_required(views.CompanyUpdate.as_view()), name="update_company"),
    path("create-contact/", login_required(views.ContactCreate.as_view()), name="create_contact"),

    path("add_company_to_holding/<int:holding_id>/", login_required(views.add_company_to_holding), name="add_company_to_holding"),  

    # Компанія (деталі)
    path("company/add_contact/<str:edrpou>/", login_required(views.add_contact), name="add_contact"),
    path("company/edit_contact/<str:edrpou>/<int:id_contact>/", login_required(views.edit_contact), name="edit_contact"),
    path("company/add_holding/<str:edrpou>/", login_required(views.add_holding), name="add_holding"),
    path("company/edit_holding/<str:edrpou>/<int:holding_id>/", login_required(views.edit_holding), name="edit_holding"),
    path("company/add_phone/<str:edrpou>/", login_required(views.add_phone), name="add_phone"),
    path("company/edit_phone/<str:edrpou>/<int:id_phone>/", login_required(views.edit_phone), name="edit_phone"),
    path("company/add_call/<str:edrpou>/<int:id_phone>/", login_required(views.add_call), name="add_call"),
    path("company/edit_call/<int:id_call>/", login_required(views.edit_call), name="edit_call"),
    path("company/calls_of_company/<str:edrpou>/", login_required(views.calls_of_company), name="calls_of_company"),
    path("company/show_all_company_links/<str:edrpou>/", login_required(views.show_all_company_links), name="show_all_company_links"),

    # Планування дзвінків
    path("company/plan_call/<str:edrpou>/", login_required(views.add_plan_call), name="plan_call_company"),
    path("company/plan_call/<str:edrpou>/<int:id_phone>/<int:id_call>/",
         login_required(views.add_plan_call),
         name="plan_call_phone_call"),
    path("company/edit_plan_call/<int:id_plan_call>/",
         login_required(views.edit_plan_call),
         name="edit_plan_call"),
]
