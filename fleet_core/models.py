# fleet_core/models.py

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

# --- DEFINICJE STAŁYCH ---

ROLES = (
    ('ADMIN', 'Administrator'),
    ('MANAGER', 'Menedżer Floty'),
    ('DRIVER', 'Kierowca'),
    ('EMPLOYEE', 'Pracownik (Dział HR/Finanse)'),
)

FUEL_TYPES = [
    ('BENZYNA', 'Benzyna'),
    ('DIESEL', 'Diesel'),
    ('ELECTRIC', 'Elektryczny'),
    ('HYBRID', 'Hybryda'),
    ('PHEV', 'Hybryda Plug-in'),
    ('LPG', 'LPG'),
    ('CNG', 'CNG'),
    ('HYDROGEN', 'Wodorowy'),
]


# --- MODELE ---

class FleetCompany(models.Model):
    nazwa = models.CharField(max_length=255)
    nip = models.CharField(max_length=10)
    data_utworzenia = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nazwa


# Rozszerzony User
class CustomUser(AbstractUser):
    rola = models.CharField(max_length=50, choices=ROLES, default='EMPLOYEE')
    pin_2fa = models.CharField(max_length=6, blank=True, null=True, verbose_name="PIN 2FA")


class Vehicle(models.Model):
    """
    Model reprezentujący fizyczny pojazd w bazie danych,
    zawierający logikę walidacyjną dla Panelu Admina.
    """
    vin = models.CharField(max_length=17, unique=True, verbose_name="Numer VIN")
    registration_number = models.CharField(max_length=10, db_index=True)
    marka = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(max_length=100, blank=True, null=True)
    data_pierwszej_rejestracji = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    STATUS_CHOICES = [
        ('SPRAWNY', 'Sprawny'),
        ('NIESPRAWNY', 'Niesprawny'),
    ]

    TYPE_CHOICES = [
        ('OSOBOWE', 'Osobowe'),
        ('CIEZAROWE', 'Ciężarowe'),
        ('AUTOBUSY', 'Autobusy'),
        ('MOTOCYKLE', 'Motocykle'),
        ('SEDAN', 'Sedan'),
        ('SUV', 'SUV'),
        ('HATCHBACK', 'Hatchback'),
        ('KOMBI', 'Kombi'),
        ('COUPE', 'Coupé'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SPRAWNY')
    typ_pojazdu = models.CharField(max_length=30, choices=TYPE_CHOICES, default='OSOBOWE')
    uwagi = models.TextField(blank=True, null=True)

    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPES,
        default='DIESEL',
        verbose_name="Rodzaj Paliwa"
    )

    assigned_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_vehicles'
    )

    przebieg = models.FloatField(default=0.0)
    company = models.ForeignKey(FleetCompany, on_delete=models.SET_NULL, null=True, blank=True)

    scan_registration_card = models.FileField(upload_to='docs/dowody/', verbose_name="Skan Dowodu Rej.", null=True, blank=True)
    scan_policy_oc = models.FileField(upload_to='docs/oc/', verbose_name="Polisa OC", null=True, blank=True)
    scan_policy_ac = models.FileField(upload_to='docs/ac/', verbose_name="Polisa AC", null=True, blank=True)
    scan_tech_inspection = models.FileField(upload_to='docs/badania/', verbose_name="Badanie Techniczne", null=True, blank=True)
    scan_service_book = models.FileField(upload_to='docs/serwis/', verbose_name="Książka Serwisowa", null=True, blank=True)
    scan_purchase_invoice = models.FileField(upload_to='docs/faktury/', verbose_name="Faktura Zakupu", null=True, blank=True)

    def __str__(self):
        return f"{self.registration_number} ({self.vin})"

    def clean(self):
        if self.przebieg < 0:
            raise ValidationError({
                'przebieg': 'Błąd ERR-02: Przebieg nie może być wartością ujemną.'
            })
        if len(self.vin) != 17:
            raise ValidationError({
                'vin': 'Błąd ERR-04: Numer VIN musi składać się z dokładnie 17 znaków.'
            })
        if not self.vin.isalnum():
            raise ValidationError({
                'vin': 'Błąd ERR-04: Numer VIN może zawierać tylko litery i cyfry.'
            })

    class Meta:
        db_table = 'app_vehicles'


class Driver(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='driver_profile', on_delete=models.CASCADE)
    numer_prawa_jazdy = models.CharField(max_length=50)
    data_waznosci_prawa_jazdy = models.DateField(null=True, blank=True)
    company = models.ForeignKey(FleetCompany, on_delete=models.SET_NULL, null=True, blank=True)

    kategorie_prawa_jazdy = models.CharField(
        max_length=100,
        default='B',
        verbose_name="Kategorie (np. B, C)"
    )
    data_waznosci_badan = models.DateField(
        null=True,
        blank=True,
        verbose_name="Ważność badań lekarskich"
    )
    aktywny = models.BooleanField(default=True)

    def __str__(self):
        name = self.user.username if self.user else "Nieznany"
        return f"{name} - {self.kategorie_prawa_jazdy}"


# --- ZDARZENIA SERWISOWE (POPRAWIONA KLASA - TYLKO JEDNA) ---
class ServiceEvent(models.Model):
    """
    Model reprezentujący zdarzenie serwisowe, naprawę lub inspekcję.
    """
    pojazd = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='service_history')
    opis = models.TextField(verbose_name="Opis Serwisu/Naprawy")
    data_serwisu = models.DateField(verbose_name="Data Serwisu")
    koszt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    typ_zdarzenia = models.CharField(
        max_length=50,
        choices=[
            ('INSPEKCJA', 'Inspekcja'),
            ('NAPRAWA', 'Naprawa/Serwis'),
            ('PRZEGLAD', 'Przegląd okresowy'),
            ('BADANIE_TECH', 'Badanie Techniczne'),
            ('LEGALIZACJA', 'Legalizacja (Tachograf)'),
        ],
        default='NAPRAWA'
    )

    def __str__(self):
        nr_rej = self.pojazd.registration_number if self.pojazd else "Brak pojazdu"
        return f"Serwis {nr_rej} ({self.data_serwisu})"

    class Meta:
        verbose_name = "Zdarzenie Serwisowe"
        verbose_name_plural = "Zdarzenia Serwisowe"


class InsurancePolicy(models.Model):
    pojazd = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='policies')
    numer_polisy = models.CharField(max_length=100, verbose_name="Numer Polisy")
    ubezpieczyciel = models.CharField(max_length=100, verbose_name="Towarzystwo Ubezpieczeniowe")
    data_waznosci_oc = models.DateField(verbose_name="Ważność OC")
    data_waznosci_ac = models.DateField(verbose_name="Ważność AC", null=True, blank=True)
    koszt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Polisa {self.numer_polisy} ({self.pojazd.registration_number})"

    class Meta:
        verbose_name = "Polisa Ubezpieczeniowa"
        verbose_name_plural = "Polisy Ubezpieczeniowe"


class DamageEvent(models.Model):
    pojazd = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='damage_history')
    opis = models.TextField(verbose_name="Opis Szkody")
    data_zdarzenia = models.DateField(verbose_name="Data Zdarzenia")
    szacowany_koszt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    zgloszony_do_ubezpieczyciela = models.BooleanField(default=False)

    status_naprawy = models.CharField(
        max_length=50,
        choices=[
            ('ZGLOSZONA', 'Zgłoszona'),
            ('WYCENIANA', 'Wyceniana'),
            ('W_NAPRAWIE', 'W naprawie'),
            ('ZAMKNIETA', 'Zamknięta'),
        ],
        default='ZGLOSZONA'
    )

    def __str__(self):
        return f"Szkoda {self.pojazd.registration_number} z dnia {self.data_zdarzenia}"

    class Meta:
        verbose_name = "Zdarzenie Szkodowe"
        verbose_name_plural = "Zdarzenia Szkodowe"


class VehicleHandover(models.Model):
    kierowca = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='handovers')
    pojazd = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='handovers')

    # --- NOWE POLE: Link do Rezerwacji (dla ID_rezerwacji) ---
    reservation = models.ForeignKey('Reservation', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name="Źródłowa Rezerwacja")

    data_wydania = models.DateField(verbose_name="Data Wydania")
    data_zwrotu = models.DateField(verbose_name="Data Zwrotu", null=True, blank=True)
    uwagi = models.TextField(blank=True, null=True)

    # --- NOWE POLA: Pliki Dokumentów ---
    scan_agreement = models.FileField(upload_to='handovers/umowy/', verbose_name="Umowa Najmu", null=True, blank=True)
    scan_handover_protocol = models.FileField(upload_to='handovers/protokoly_wydania/', verbose_name="Protokół Wydania",
                                              null=True, blank=True)
    scan_return_protocol = models.FileField(upload_to='handovers/protokoly_zwrotu/', verbose_name="Protokół Zwrotu",
                                            null=True, blank=True)

    def __str__(self):
        return f"{self.pojazd} -> {self.kierowca} ({self.data_wydania})"


# ----------------------------------------------------
# MODEL REZERWACJI (NOWE)
# ----------------------------------------------------
class Reservation(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Imię Kierowcy")
    last_name = models.CharField(max_length=100, verbose_name="Nazwisko Kierowcy")

    # ZMIANA: Zamiast ForeignKey, zwykłe pole tekstowe
    company = models.CharField(max_length=200, verbose_name="Nazwa Firmy")

    date_from = models.DateField(verbose_name="Data Od", null=True, blank=True)
    date_to = models.DateField(verbose_name="Data Do", null=True, blank=True)

    vehicle_type = models.CharField(
        max_length=30,
        choices=Vehicle.TYPE_CHOICES,
        verbose_name="Typ Pojazdu"
    )

    assigned_vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,  # Jeśli usuniesz auto, rezerwacja zostanie (z pustym polem)
        null=True,
        blank=True,
        verbose_name="Przypisany Pojazd"
    )

    driver = models.ForeignKey(
        'Driver',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Powiązany Kierowca (Konto)"
    )

    additional_info = models.TextField(
        verbose_name="Dodatkowe informacje",
        null=True,
        blank=True
    )

    scan_agreement = models.FileField(
        upload_to='umowy/',  # Pliki trafią do folderu media/umowy/
        verbose_name="Skan Umowy (PDF)",
        null=True,
        blank=True
    )

    # NOWE POLE: STATUS
    STATUS_CHOICES = [
        ('OCZEKUJACE', 'Oczekujące'),
        ('PRZYJETE', 'Przyjęte'),
        ('ZATWIERDZONE', 'Zatwierdzone'),
        ('ODRZUCONE', 'Odrzucone'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='OCZEKUJACE',
        verbose_name="Status Rezerwacji"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rezerwacja: {self.first_name} {self.last_name} ({self.status})"

    class Meta:
        verbose_name = "Rezerwacja"
        verbose_name_plural = "Rezerwacje"

class ReservationFile(models.Model):
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='attachments' # To pozwoli odwoływać się: rezerwacja.attachments.all()
    )
    file = models.FileField(upload_to='umowy/', verbose_name="Plik")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Plik {self.id} dla rezerwacji {self.reservation_id}"

class VehicleDocument(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents', verbose_name="Pojazd")
    title = models.CharField(max_length=200, verbose_name="Nazwa Dokumentu")
    file = models.FileField(upload_to='pojazdy_docs/', verbose_name="Plik")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True, verbose_name="Opis/Uwagi")

    def __str__(self):
        return f"{self.title} ({self.vehicle.registration_number})"