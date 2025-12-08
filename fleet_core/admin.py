# Master/Server/fleet_core/admin.py

from django.contrib import admin
# DODANO ServiceEvent, które wcześniej dodaliśmy do models.py
from .models import FleetCompany, Vehicle, CustomUser, Driver, ServiceEvent, DamageEvent # Dodaj DamageEvent

# -----------------------------------------------
# Rejestracja modelu Zdarzenia Serwisowego
# -----------------------------------------------
# Używamy dekoratora, aby dodać szczegółowe opcje wyświetlania (list_display)
@admin.register(ServiceEvent)
class ServiceEventAdmin(admin.ModelAdmin):
    list_display = ('pojazd', 'data_serwisu', 'typ_zdarzenia', 'koszt')
    list_filter = ('typ_zdarzenia', 'data_serwisu')
    search_fields = ('opis', 'pojazd__registration_number')


# -----------------------------------------------
# Rejestracja pozostałych modeli (możesz użyć dekoratora dla spójności)
# -----------------------------------------------
# Rejestracja Firmy
@admin.register(FleetCompany)
class FleetCompanyAdmin(admin.ModelAdmin):
    list_display = ('nazwa', 'nip')

# Rejestracja Pojazdów (ulepszona lista pól)
@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'vin', 'przebieg', 'company', 'is_active')
    list_filter = ('is_active', 'company')
    search_fields = ('registration_number', 'vin')

# Rejestracja Użytkowników i Kierowców (jeśli chcesz ich edytować)
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'rola')

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'numer_prawa_jazdy', 'aktywny')
    search_fields = ('user__username', 'numer_prawa_jazdy')

# Dodaj nową rejestrację:
@admin.register(DamageEvent)
class DamageEventAdmin(admin.ModelAdmin):
    list_display = ('pojazd', 'data_zdarzenia', 'status_naprawy', 'szacowany_koszt')
    list_filter = ('status_naprawy', 'zgloszony_do_ubezpieczyciela')