# forms.py
from django import forms
from .models import Company, ContactPerson, Phone, District, Holding, Call, CallPlan
from .checkers import check_edrpou, check_phone, check_person
from django.utils import timezone




class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['edrpou', 'name', 'status', 'legal_address', 'region', 'district', 'hectares']
        labels = {
            'edrpou': 'ЄДРПОУ',
            'name': 'Назва компанії',
            'status': 'Статус компанії',
            'legal_address': 'Юридична адреса',
            'region': 'Область',
            'district': 'Район',
            'hectares': 'Площа (га)',
        }
        widgets = {
            'edrpou': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ЄДРПОУ'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Назва компанії'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'legal_address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Юридична адреса'}),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'district': forms.Select(attrs={'class': 'form-control'}),
            'hectares': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Площа'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Якщо об'єкт вже існує і обрана область
        if self.instance and self.instance.region:
            self.fields['district'].queryset = District.objects.filter(region=self.instance.region)
        else:
            # Інакше можна показувати порожній список або всі райони
            self.fields['district'].queryset = District.objects.none()

    def clean_edrpou(self):
        edrpou = check_edrpou(self.cleaned_data.get('edrpou'))
        qs = Company.objects.filter(edrpou=edrpou)
        if self.instance.pk:  # якщо редагуємо існуючу компанію
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            self.duplicate_found = True
            raise forms.ValidationError("Компанія з таким ЄДРПОУ вже існує")
        return edrpou
        

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactPerson
        fields = ['full_name', 'position']
        labels = {
            'full_name': 'ПІБ',
            'position': 'Посада',
        }
    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name", "").strip()

        if full_name:  # якщо не порожнє
            full_name = check_person(full_name)
        else:
            raise forms.ValidationError("Ім’я контакту не може бути порожнім")
        
        return full_name


class PhoneForm(forms.ModelForm):
    number = forms.CharField(required=False)
    class Meta:
        model = Phone
        fields = ['number', 'status']
    
    def clean_number(self):
        number = self.cleaned_data.get("number")
        if number:  # якщо не порожнє
            number = check_phone(number)
        else:
            raise forms.ValidationError("Номер телефону не може бути порожнім!!!")
        return number
    
    def validate_unique(self):
        # пропускаємо унікальність
        pass
    

class HoldingForm(forms.ModelForm):
    class Meta:
        model = Holding
        fields = ['name']
    
    def validate_unique(self):
        # пропускаємо унікальність
        pass


class CallForm(forms.ModelForm):
    class Meta:
        model = Call
        fields = ["duration_seconds", "notes", "datetime"]  # company і phone не показуємо
        widgets = {
            "datetime": forms.DateTimeInput(
                format="%Y-%m-%d %H:%M",
                attrs={
                    "type": "datetime-local",  # HTML5 елемент вибору дати й часу
                    "class": "form-control",
                },
            ),
        }

    def __init__(self, *args, company=None, phone=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._company = company
        self._phone = phone

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self._phone:
            instance.phone = self._phone
        if commit:
            instance.save()
            if self._company:
                instance.company.set([self._company])  # бо M2M
        return instance
    

class PlanCallForm(forms.ModelForm):
    class Meta:
        model = CallPlan
        fields = ["planned_datetime", "notes", "status"]
        widgets = {
            "planned_datetime": forms.DateTimeInput(
                format="%Y-%m-%d %H:%M",
                attrs={
                    "type": "datetime-local",  # HTML5 елемент вибору дати й часу
                    "class": "form-control",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # підказує Django, в якому форматі парсити дату з input
        self.fields["planned_datetime"].input_formats = ["%Y-%m-%d %H:%M"]


