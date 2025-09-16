from django.db import models
from django.utils import timezone


class Holding(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Region(models.Model):
    region = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return self.region


class District(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="districts")
    district = models.CharField(max_length=32)

    class Meta:
        unique_together = ("region", "district")  # унікальність комбінації

    def __str__(self):
        return f"{self.district} ({self.region})"


class CompanyStatus(models.Model):
    status_name = models.CharField(max_length=32, unique=True)
    
    def __str__(self):
        return self.status_name


class Company(models.Model):
    holding = models.ForeignKey(
        Holding, on_delete=models.SET_NULL, null=True, blank=True, related_name="companies"
    )
    status = models.ForeignKey(
        CompanyStatus, on_delete=models.SET_NULL, default=1, null=True, blank=True, related_name="companies"
    )
    edrpou = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=255)
    legal_address = models.TextField(blank=True, null=True)
    hectares = models.IntegerField(blank=True, null=True)  # якщо потрібні дроби
    region = models.ForeignKey(
        Region, on_delete=models.SET_NULL, null=True, blank=True, related_name="companies"
    )
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True, related_name="companies"
    )

    def __str__(self):
        return f"{self.name} ({self.edrpou})"


class CompanyEmail(models.Model):
    email = models.EmailField(unique=True)
    companies = models.ManyToManyField("Company", related_name="emails", blank=True)

    def __str__(self):
        return self.email


class ContactPerson(models.Model):
    companies = models.ManyToManyField("Company", related_name="contacts", blank=True) #related_name="contacts" задає ім’я, за яким можна з Company отримати всіх її контактних осіб.
    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} ({self.position})"


class Phone(models.Model):
    STATUS_CHOICES = [
        ("on", "Active"),
        ("off", "Inactive"),
    ]

    contact = models.ForeignKey(ContactPerson, on_delete=models.SET_NULL, related_name="phones", null=True, blank=True)
    number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default="on")
    companies = models.ManyToManyField("Company", related_name="phones", blank=True)

    def __str__(self):
        return f"{self.number} [{self.status}]"


class Call(models.Model):
    phone = models.ForeignKey(Phone, on_delete=models.SET_NULL, related_name="calls", null=True, blank=True)
    company = models.ManyToManyField("Company", related_name="calls")  # для швидкого пошуку по ЄДРПОУ
    datetime = models.DateTimeField(default=timezone.now)   # час дзвінка
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Call to {self.phone.number} on {self.datetime}"


class CallPlan(models.Model):
    STATUS_CHOICES = [
        ("on", "Active"),
        ("off", "Inactive"),
    ]

    call = models.OneToOneField(Call, on_delete=models.CASCADE, related_name="next_plan", null=True, blank=True)
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name="planned_calls", null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="planned_calls")
    planned_datetime = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default="on")


    def __str__(self):
        return f"Plan for {self.company.name} on {self.planned_datetime}"


class Warehouse(models.Model):
    name = models.CharField(max_length=255, unique=True, default="Склад")
    TRANSPORT_CHOICES = [
        ("rail", "Railway"),
        ("auto", "Automobile"),
        ("port", "Port"),
        ("other", "Other"),
    ]

    # Власники складу
    owners = models.ManyToManyField(
        Company,
        related_name="owned_warehouses",
        blank=True
    )

    # Клієнти (компанії, що зберігають продукцію на складі)
    clients = models.ManyToManyField(
        Company,
        related_name="used_warehouses",
        blank=True
    )

    capacity_tons = models.DecimalField(max_digits=12, decimal_places=2)  # Ємність, т
    transport_type = models.CharField(max_length=10, choices=TRANSPORT_CHOICES, default="auto")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    region = models.ForeignKey(
        Region, on_delete=models.SET_NULL, null=True, blank=True, related_name="warehouses"
    )
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True, related_name="warehouses"
    )

    def __str__(self):
        return f"Warehouse {self.capacity_tons} t ({self.get_transport_type_display()})"


class Crop(models.Model):
    name = models.CharField(max_length=100, unique=True)


class StockItem(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="stock_items")
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)