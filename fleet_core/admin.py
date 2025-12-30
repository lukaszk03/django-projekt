# Master/Server/fleet_core/admin.py

from django.contrib import admin
from .models import FleetCompany, Vehicle, CustomUser, Driver, ServiceEvent, DamageEvent, InsurancePolicy, VehicleHandover

@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ('numer_polisy', 'pojazd', 'ubezpieczyciel', 'data_waznosci_oc')
    list_filter = ('ubezpieczyciel', 'data_waznosci_oc')

@admin.register(FleetCompany)
class FleetCompanyAdmin(admin.ModelAdmin):
    list_display = ('nazwa', 'nip')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'vin', 'przebieg', 'company', 'is_active')
    list_filter = ('is_active', 'company')
    search_fields = ('registration_number', 'vin')

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'rola')

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'numer_prawa_jazdy', 'aktywny')
    search_fields = ('user__username', 'numer_prawa_jazdy')

@admin.register(DamageEvent)
class DamageEventAdmin(admin.ModelAdmin):
    list_display = ('pojazd', 'data_zdarzenia', 'status_naprawy', 'szacowany_koszt')
    list_filter = ('status_naprawy', 'zgloszony_do_ubezpieczyciela')

@admin.register(VehicleHandover)
class VehicleHandoverAdmin(admin.ModelAdmin):
    list_display = ('pojazd', 'kierowca', 'data_wydania', 'data_zwrotu')
    list_filter = ('data_wydania', 'data_zwrotu')
    search_fields = ('pojazd__registration_number', 'kierowca__user__last_name', 'kierowca__user__first_name')