from django.test import TestCase
from calling_app.models import Company, CompanyStatus, ContactPerson, Phone, Holding, Warehouse
from calling_app.utils import search_in_queryset


class SearchInQuerysetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # створюємо статус один раз для всіх тестів
        cls.status_c, _ = CompanyStatus.objects.get_or_create(status_name="active")
        # створюємо холдинг
        cls.holding = Holding.objects.create(name="AgroHolding")

    def setUp(self):
        # створюємо компанії
        self.c1 = Company.objects.create(
            name="AgroTest",
            edrpou="12345678",
            legal_address="Kyiv",
            status=self.__class__.status_c,
            holding=self.__class__.holding
        )
        self.c2 = Company.objects.create(
            name="Sunflower Ltd",
            edrpou="87654321",
            legal_address="Lviv",
            status=self.__class__.status_c
        )

        # контакт для компанії 1
        self.contact = ContactPerson.objects.create(full_name="Ivanov Ivan")
        self.contact.companies.add(self.c1)

        # телефон для компанії 2
        self.phone = Phone.objects.create(number="+380971234567", status="on")
        self.phone.companies.add(self.c2)

        # створюємо склад і зв’язуємо з компанією 1
        self.warehouse = Warehouse.objects.create(name="Main Warehouse", capacity_tons=100)
        self.warehouse.clients.add(self.c1)
        self.warehouse.owners.add(self.c1)

    def test_search_by_name(self):
        qs = search_in_queryset(Company.objects.all(), "Agro")
        assert list(qs) == [self.c1]

    def test_search_by_edrpou(self):
        qs = search_in_queryset(Company.objects.all(), "87654321")
        assert list(qs) == [self.c2]

    def test_search_by_address(self):
        qs = search_in_queryset(Company.objects.all(), "Kyiv")
        assert list(qs) == [self.c1]

    def test_search_by_holding_name(self):
        qs = search_in_queryset(Company.objects.all(), "AgroHolding")
        assert list(qs) == [self.c1]

    def test_search_by_contact_name(self):
        qs = search_in_queryset(Company.objects.all(), "Ivanov")
        assert list(qs) == [self.c1]

    def test_search_by_phone_number(self):
        qs = search_in_queryset(Company.objects.all(), "+3809712")
        assert list(qs) == [self.c2]

    def test_search_by_warehouse_name(self):
        qs = search_in_queryset(Company.objects.all(), "Main Warehouse")
        assert list(qs) == [self.c1]

    def test_empty_search_returns_all(self):
        qs = search_in_queryset(Company.objects.all(), "")
        assert set(qs) == {self.c1, self.c2}
