# Master/Server/fleet_core/serializers.py

from rest_framework import serializers
# DODAJ IMPORT InsurancePolicy
from .models import Vehicle, Driver, ServiceEvent, DamageEvent, FleetCompany, InsurancePolicy

# 1. SERIALIZER DLA POJAZDÓW (VehicleDto)
class VehicleDto(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.nazwa', read_only=True)
    fuel_type_display = serializers.CharField(source='get_fuel_type_display', read_only=True)
    assigned_user_name = serializers.ReadOnlyField(source='assigned_user.get_full_name')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    typ_display = serializers.CharField(source='get_typ_pojazdu_display', read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'vin', 'registration_number', 'company', 'company_name',
            'is_active', 'przebieg', 'fuel_type', 'fuel_type_display',
            'marka', 'model', 'data_pierwszej_rejestracji', 'assigned_user', 'assigned_user_name',
            'status', 'status_display', 'typ_pojazdu', 'typ_display', 'uwagi'
        ]

# 2. SERIALIZER DLA UŻYTKOWNIKÓW (Kierowców)
class DriverDto(serializers.ModelSerializer):
    first_name = serializers.ReadOnlyField(source='user.first_name', default='')
    last_name = serializers.ReadOnlyField(source='user.last_name', default='')
    # Weryfikacja: Czy user_name poprawnie mapuje się do pola 'username' w CustomUser?
    user_name = serializers.ReadOnlyField(source='user.username', default='Brak loginu')
    email = serializers.ReadOnlyField(source='user.email', default='Brak email')
    company_name = serializers.CharField(source='company.nazwa', read_only=True)  # Tylko do odczytu

    class Meta:
        model = Driver
        fields = [
            'id', 'user', 'user_name', 'first_name', 'last_name', 'email',
            'numer_prawa_jazdy', 'kategorie_prawa_jazdy',
            'data_waznosci_badan', 'company', 'company_name'
        ]

# 3. SERIALIZER DLA ZDARZEŃ SERWISOWYCH (ServiceEventDto)
class ServiceEventDto(serializers.ModelSerializer):
    pojazd_nr_rej = serializers.CharField(source='pojazd.registration_number', read_only=True)

    class Meta:
        model = ServiceEvent # Używamy ServiceEvent
        fields = ['id', 'opis', 'koszt', 'data_serwisu', 'pojazd_nr_rej']


# 4. SERIALIZER DLA ZDARZEŃ SZKODOWYCH (DamageEventDto)
class DamageEventDto(serializers.ModelSerializer):
    pojazd_nr_rej = serializers.CharField(source='pojazd.registration_number', read_only=True)

    class Meta:
        model = DamageEvent
        fields = ['id', 'pojazd', 'pojazd_nr_rej', 'opis', 'data_zdarzenia', 'szacowany_koszt', 'zgloszony_do_ubezpieczyciela', 'status_naprawy']
        # Pole 'pojazd' jest potrzebne do tworzenia/aktualizacji
        extra_kwargs = {'pojazd': {'write_only': True}}


# 5. NOWY SERIALIZER DLA POLIS
class InsurancePolicyDto(serializers.ModelSerializer):
    pojazd_nr_rej = serializers.CharField(source='pojazd.registration_number', read_only=True)

    class Meta:
        model = InsurancePolicy
        fields = ['id', 'pojazd', 'pojazd_nr_rej', 'numer_polisy', 'ubezpieczyciel', 'data_waznosci_oc', 'data_waznosci_ac', 'koszt']
        extra_kwargs = {'pojazd': {'write_only': True}}