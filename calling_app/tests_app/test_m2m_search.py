from django.test import TestCase
from calling_app.models import ContactPerson, Phone, Company, CompanyStatus
from calling_app.utils import get_search_model_filds_m2m
from django.db.models import Q, QuerySet, CharField, TextField, ForeignKey, OneToOneField, ManyToManyField

def get_search_model_filds_m2m(model):
    fields_list = []
    for field in model._meta.get_fields():
    # ManyToMany (включаючи related_name)
        if isinstance(field, ManyToManyField):
            related_model = field.remote_field.model  # <-- тут краще remote_field.model
            for subfield in related_model._meta.get_fields():
                # перевіряємо тільки локальні текстові поля
                if isinstance(subfield, (CharField, TextField)) and not subfield.many_to_many and not subfield.auto_created:
                    field_name = f"{field.name}__{subfield.name}__icontains"
                    fields_list.append(field_name)
    return fields_list

print(get_search_model_filds_m2m(Company))