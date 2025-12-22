# fleet_core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError  # <-- Upewnij się, że to masz!

# Definicja dostępnych ról
ROLES = (
    ('ADMIN', 'Administrator'),
    ('MANAGER', 'Menedżer Floty'),
    ('DRIVER', 'Kierowca'),
    ('EMPLOYEE', 'Pracownik (Dział HR/Finanse)'),
)

# Model Firmy (Najemcy) - zakładamy, że istnieje w tym samym pliku
class FleetCompany(models.Model):
    nazwa = models.CharField(max_length=255)
    nip = models.CharField(max_length=10)
    data_utworzenia = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nazwa

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
# ----------------------------------------------------
# MODEL POJAZDU Z WALIDACJĄ ZGODNĄ Z ERR-02 i ERR-04
# ----------------------------------------------------
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
    # Definicja typów paliwa (możesz to dać nad klasą Vehicle)
    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPES,
        default='DIESEL',
        verbose_name="Rodzaj Paliwa"
    )

    assigned_user = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_vehicles'
    )

    # Przebieg (float wg diagramu)
    przebieg = models.FloatField(default=0.0)

    # Relacja do Firmy
    # company = models.ForeignKey(FleetCompany, on_delete=models.CASCADE, related_name='vehicles')
    company = models.ForeignKey(FleetCompany, on_delete=models.SET_NULL, null=True, blank=True) #wersja tymczasowa
    def __str__(self):
        return f"{self.registration_number} ({self.vin})"

    def clean(self):
        """
        Walidacja na poziomie modelu. Używana automatycznie przez Panel Admina.
        """
        # 1. Walidacja Przebiegu (Implementacja dla ERR-02)
        if self.przebieg < 0:
            raise ValidationError({
                'przebieg': 'Błąd ERR-02: Przebieg nie może być wartością ujemną. Jest to błąd walidacji krytycznej.'
            })

        # 2. Walidacja VIN (Implementacja dla ERR-04 - rozszerzona walidacja serwerowa)
        if len(self.vin) != 17:
            raise ValidationError({
                'vin': 'Błąd ERR-04: Numer VIN musi składać się z dokładnie 17 znaków.'
            })
        if not self.vin.isalnum():
            raise ValidationError({
                'vin': 'Błąd ERR-04: Numer VIN może zawierać tylko litery i cyfry.'
            })

        # Opcjonalna walidacja unikalności VIN, jeśli jest potrzebna
        # if Vehicle.objects.filter(vin=self.vin).exclude(pk=self.pk).exists():
        #     raise ValidationError({'vin': 'Pojazd o tym numerze VIN już istnieje.'})

    class Meta:
        db_table = 'app_vehicles'


# Model Kierowcy 
class Driver(models.Model):
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE)
    numer_prawa_jazdy = models.CharField(max_length=50)
    data_waznosci_prawa_jazdy = models.DateField()

    # --- NOWE POLA ---
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
    # -----------------

    aktywny = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.kategorie_prawa_jazdy}"

# Rozszerzony User
class CustomUser(AbstractUser):
    # Poprawiamy 'default' na jedną z zdefiniowanych stałych, np. 'EMPLOYEE'
    rola = models.CharField(max_length=50, choices=ROLES, default='EMPLOYEE')
    # Dodatkowe pole, które posłuży do 2FA dla administratorów
    pin_2fa = models.CharField(max_length=6, blank=True, null=True, verbose_name="PIN 2FA")

# Master/Server/fleet_core/models.py (DODAJ NA KOŃCU PLIKU)

# ----------------------------------------------------
# MODEL ZDARZEŃ SERWISOWYCH (ServiceEvent)
# ----------------------------------------------------
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
            ('BADANIE_TECH', 'Badanie Techniczne'),  # <-- NOWE
            ('LEGALIZACJA', 'Legalizacja (Tachograf)'),  # <-- NOWE
        ],
        default='NAPRAWA'
    )

    def __str__(self):
        return f"Serwis {self.pojazd.registration_number} ({self.data_serwisu})"

    class Meta:
        verbose_name = "Zdarzenie Serwisowe"
        verbose_name_plural = "Zdarzenia Serwisowe"


# 2. NOWY MODEL: POLISY (Dodaj na samym końcu pliku)
class InsurancePolicy(models.Model):
    pojazd = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='policies')
    numer_polisy = models.CharField(max_length=100, verbose_name="Numer Polisy")
    ubezpieczyciel = models.CharField(max_length=100, verbose_name="Towarzystwo Ubezpieczeniowe")

    # Daty ważności
    data_waznosci_oc = models.DateField(verbose_name="Ważność OC")
    data_waznosci_ac = models.DateField(verbose_name="Ważność AC", null=True, blank=True)

    koszt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Polisa {self.numer_polisy} ({self.pojazd.registration_number})"

    class Meta:
        verbose_name = "Polisa Ubezpieczeniowa"
        verbose_name_plural = "Polisy Ubezpieczeniowe"


# Master/Server/fleet_core/models.py (DODAJ NA KOŃCU PLIKU)

# ----------------------------------------------------
# MODEL ZDARZEŃ SERWISOWYCH
# ----------------------------------------------------
class ServiceEvent(models.Model):
    """
    Model reprezentujący zdarzenie serwisowe, naprawę lub inspekcję.
    """
    # Relacja do istniejącego modelu Vehicle
    pojazd = models.ForeignKey('Vehicle', on_delete=models.CASCADE, related_name='service_history')

    opis = models.TextField(verbose_name="Opis Serwisu/Naprawy")
    data_serwisu = models.DateField(verbose_name="Data Serwisu")

    # Koszt jako liczba z dwoma miejscami po przecinku (do rozliczeń)
    koszt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Kategoria zdarzenia (dla łatwiejszego filtrowania)
    typ_zdarzenia = models.CharField(
        max_length=50,
        choices=[
            ('INSPEKCJA', 'Inspekcja/Badanie Tech.'),
            ('NAPRAWA', 'Naprawa/Serwis'),
            ('PRZEGLAD', 'Przegląd okresowy'),
        ],
        default='NAPRAWA'
    )

    def __str__(self):
        return f"Serwis {self.pojazd.registration_number} ({self.data_serwisu})"

    class Meta:
        verbose_name = "Zdarzenie Serwisowe"
        verbose_name_plural = "Zdarzenia Serwisowe"


# Master/Server/fleet_core/models.py (DODAJ NA KOŃCU PLIKU)

# ----------------------------------------------------
# MODEL ZDARZEŃ SZKODOWYCH (DamageEvent)
# ----------------------------------------------------
class DamageEvent(models.Model):
    """
    Model reprezentujący zdarzenie szkodowe (stłuczka, awaria, akt wandalizmu).
    """
    pojazd = models.ForeignKey('Vehicle', on_delete=models.CASCADE, related_name='damage_history')
    opis = models.TextField(verbose_name="Opis Szkody")
    data_zdarzenia = models.DateField(verbose_name="Data Zdarzenia")
    szacowany_koszt = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    zgloszony_do_ubezpieczyciela = models.BooleanField(default=False)

    # Dodatkowe pole, które może być użyte do statusu naprawy
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