# Master/Server/fleet_core/serializers.py

from rest_framework import serializers
from .models import Vehicle, Driver, ServiceEvent, DamageEvent, FleetCompany, InsurancePolicy, VehicleHandover

# 1. SERIALIZER DLA POJAZDÓW
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

# 2. SERIALIZER DLA UŻYTKOWNIKÓW
class DriverDto(serializers.ModelSerializer):
    first_name = serializers.ReadOnlyField(source='user.first_name', default='')
    last_name = serializers.ReadOnlyField(source='user.last_name', default='')
    user_name = serializers.ReadOnlyField(source='user.username', default='Brak loginu')
    email = serializers.ReadOnlyField(source='user.email', default='Brak email')
    company_name = serializers.CharField(source='company.nazwa', read_only=True)

    class Meta:
        model = Driver
        fields = [
            'id', 'user', 'user_name', 'first_name', 'last_name', 'email',
            'numer_prawa_jazdy', 'kategorie_prawa_jazdy',
            'data_waznosci_badan', 'company', 'company_name'
        ]

# 3. SZKODY
class DamageEventDto(serializers.ModelSerializer):
    pojazd_nr_rej = serializers.CharField(source='pojazd.registration_number', read_only=True)

    class Meta:
        model = DamageEvent
        fields = ['id', 'pojazd', 'pojazd_nr_rej', 'opis', 'data_zdarzenia', 'szacowany_koszt',
                  'zgloszony_do_ubezpieczyciela', 'status_naprawy']

# 4. POLISY
class InsurancePolicyDto(serializers.ModelSerializer):
    pojazd_nr_rej = serializers.CharField(source='pojazd.registration_number', read_only=True)
    # DODANO: Numer VIN (niezbędny do wyświetlenia w tabeli)
    pojazd_vin = serializers.ReadOnlyField(source='pojazd.vin')

    class Meta:
        model = InsurancePolicy
        # Dodajemy 'pojazd_vin' do listy pól
        fields = ['id', 'pojazd', 'pojazd_nr_rej', 'pojazd_vin', 'numer_polisy', 'ubezpieczyciel', 'data_waznosci_oc', 'data_waznosci_ac', 'koszt']
        extra_kwargs = {'pojazd': {'write_only': True}}

# 5. PRZEKAZANIA
class VehicleHandoverDto(serializers.ModelSerializer):
    imie = serializers.ReadOnlyField(source='kierowca.user.first_name')
    nazwisko = serializers.ReadOnlyField(source='kierowca.user.last_name')
    firma = serializers.ReadOnlyField(source='kierowca.company.nazwa')
    marka = serializers.ReadOnlyField(source='pojazd.marka')
    model = serializers.ReadOnlyField(source='pojazd.model')
    rejestracja = serializers.ReadOnlyField(source='pojazd.registration_number')

    class Meta:
        model = VehicleHandover
        fields = ['id', 'kierowca', 'pojazd', 'imie', 'nazwisko', 'firma',
                  'marka', 'model', 'rejestracja', 'data_wydania', 'data_zwrotu', 'uwagi']

# 6. ZDARZENIA SERWISOWE (Inspekcje, Przeglądy, Naprawy) - NOWE
class ServiceEventDto(serializers.ModelSerializer):
    pojazd_nr_rej = serializers.ReadOnlyField(source='pojazd.registration_number')
    # TO JEST KLUCZOWE POLE DLA CIEBIE (NR VIN):
    pojazd_vin = serializers.ReadOnlyField(source='pojazd.vin')

    class Meta:
        model = ServiceEvent
        fields = ['id', 'pojazd', 'pojazd_nr_rej', 'pojazd_vin', 'opis', 'data_serwisu', 'koszt', 'typ_zdarzenia']