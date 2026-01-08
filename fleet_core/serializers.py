# Master/Server/fleet_core/serializers.py

from rest_framework import serializers
from .models import Vehicle, Driver, ServiceEvent, DamageEvent, FleetCompany, InsurancePolicy, VehicleHandover, Reservation, ReservationFile, VehicleDocument, GlobalSettings

# 1. SERIALIZER DLA POJAZDÓW
# fleet_core/serializers.py

class VehicleDto(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.nazwa', read_only=True)
    fuel_type_display = serializers.CharField(source='get_fuel_type_display', read_only=True)
    assigned_user_name = serializers.ReadOnlyField(source='assigned_user.get_full_name')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    typ_display = serializers.CharField(source='get_typ_pojazdu_display', read_only=True)

    # --- 1. DEKLARACJA PÓL DO USUWANIA (To już pewnie masz, ale sprawdź) ---
    remove_scan_registration_card = serializers.BooleanField(write_only=True, required=False)
    remove_scan_policy_oc = serializers.BooleanField(write_only=True, required=False)
    remove_scan_policy_ac = serializers.BooleanField(write_only=True, required=False)
    remove_scan_tech_inspection = serializers.BooleanField(write_only=True, required=False)
    remove_scan_service_book = serializers.BooleanField(write_only=True, required=False)
    remove_scan_purchase_invoice = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'vin', 'registration_number', 'company', 'company_name',
            'is_active', 'przebieg', 'fuel_type', 'fuel_type_display',
            'marka', 'model', 'data_pierwszej_rejestracji', 'assigned_user', 'assigned_user_name',
            'status', 'status_display', 'typ_pojazdu', 'typ_display', 'uwagi',

            # --- 2. TUTAJ BRAKOWAŁO PÓL PLIKÓW (MODELU) ---
            'scan_registration_card',
            'scan_policy_oc',
            'scan_policy_ac',
            'scan_tech_inspection',
            'scan_service_book',
            'scan_purchase_invoice',

            # --- 3. I TUTAJ BRAKOWAŁO PÓL USUWANIA (To naprawia Twój błąd!) ---
            'remove_scan_registration_card',
            'remove_scan_policy_oc',
            'remove_scan_policy_ac',
            'remove_scan_tech_inspection',
            'remove_scan_service_book',
            'remove_scan_purchase_invoice'
        ]

    def create(self, validated_data):
        # Usuwamy pola 'remove_scan...', ponieważ przy tworzeniu nowego pojazdu
        # nie ma czego usuwać, a model bazy danych ich nie obsługuje.
        validated_data.pop('remove_scan_registration_card', None)
        validated_data.pop('remove_scan_policy_oc', None)
        validated_data.pop('remove_scan_policy_ac', None)
        validated_data.pop('remove_scan_tech_inspection', None)
        validated_data.pop('remove_scan_service_book', None)
        validated_data.pop('remove_scan_purchase_invoice', None)

        return super().create(validated_data)

    # --- 4. LOGIKA USUWANIA I AKTUALIZACJI ---
    def update(self, instance, validated_data):
        files_to_check = [
            ('scan_registration_card', 'remove_scan_registration_card'),
            ('scan_policy_oc', 'remove_scan_policy_oc'),
            ('scan_policy_ac', 'remove_scan_policy_ac'),
            ('scan_tech_inspection', 'remove_scan_tech_inspection'),
            ('scan_service_book', 'remove_scan_service_book'),
            ('scan_purchase_invoice', 'remove_scan_purchase_invoice'),
        ]

        for field_name, remove_flag in files_to_check:
            # Jeśli zaznaczono checkbox usuwania
            if validated_data.pop(remove_flag, False):
                file_field = getattr(instance, field_name)
                if file_field:
                    file_field.delete(save=False)  # Usuń plik
                    setattr(instance, field_name, None)  # Wyczyść pole w bazie

        return super().update(instance, validated_data)

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
            'data_waznosci_prawa_jazdy', 'data_waznosci_badan', 'company', 'company_name'
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
    pojazd_vin = serializers.ReadOnlyField(source='pojazd.vin')

    class Meta:
        model = InsurancePolicy
        # USUŃ LINIĘ extra_kwargs, ZOSTAWMY TYLKO FIELDS
        fields = ['id', 'pojazd', 'pojazd_nr_rej', 'pojazd_vin', 'numer_polisy', 'ubezpieczyciel', 'data_waznosci_oc', 'data_waznosci_ac', 'koszt']

# 5. PRZEKAZANIA
class VehicleHandoverDto(serializers.ModelSerializer):
    imie = serializers.ReadOnlyField(source='kierowca.user.first_name')
    nazwisko = serializers.ReadOnlyField(source='kierowca.user.last_name')
    firma = serializers.ReadOnlyField(source='kierowca.company.nazwa')
    marka = serializers.ReadOnlyField(source='pojazd.marka')
    model = serializers.ReadOnlyField(source='pojazd.model')
    rejestracja = serializers.ReadOnlyField(source='pojazd.registration_number')

    # ID Rezerwacji (zostawiamy w API, ale ukryjemy we frontendzie)
    reservation_id = serializers.ReadOnlyField(source='reservation.id')

    # Pola do usuwania plików
    remove_scan_agreement = serializers.BooleanField(write_only=True, required=False)
    remove_scan_handover_protocol = serializers.BooleanField(write_only=True, required=False)
    remove_scan_return_protocol = serializers.BooleanField(write_only=True, required=False)

    dystans = serializers.SerializerMethodField()

    class Meta:
        model = VehicleHandover
        fields = [
            'id', 'kierowca', 'pojazd', 'reservation_id',
            'imie', 'nazwisko', 'firma',
            'marka', 'model', 'rejestracja',
            'data_wydania', 'data_zwrotu', 'uwagi',

            # NOWE POLA:
            'przebieg_start', 'przebieg_stop', 'dystans',
            'paliwo_start', 'paliwo_stop',
            'stawka_za_km', 'koszt_brakujacego_paliwa', 'calkowity_koszt',

            # Pliki i usuwanie (zachowaj je)
            'scan_agreement', 'scan_handover_protocol', 'scan_return_protocol',
            'remove_scan_agreement', 'remove_scan_handover_protocol', 'remove_scan_return_protocol'
        ]

    def get_dystans(self, obj):
        if obj.przebieg_stop and obj.przebieg_start:
            return obj.przebieg_stop - obj.przebieg_start
        return 0

    def update(self, instance, validated_data):
        # Logika usuwania plików
        files_to_check = [
            ('scan_agreement', 'remove_scan_agreement'),
            ('scan_handover_protocol', 'remove_scan_handover_protocol'),
            ('scan_return_protocol', 'remove_scan_return_protocol'),
        ]
        for field, flag in files_to_check:
            if validated_data.pop(flag, False):
                f = getattr(instance, field)
                if f:
                    f.delete(save=False)
                    setattr(instance, field, None)

        return super().update(instance, validated_data)

# 6. ZDARZENIA SERWISOWE (Inspekcje, Przeglądy, Naprawy) - NOWE
class ServiceEventDto(serializers.ModelSerializer):
    pojazd_nr_rej = serializers.ReadOnlyField(source='pojazd.registration_number')
    # TO JEST KLUCZOWE POLE DLA CIEBIE (NR VIN):
    pojazd_vin = serializers.ReadOnlyField(source='pojazd.vin')

    class Meta:
        model = ServiceEvent
        fields = ['id', 'pojazd', 'pojazd_nr_rej', 'pojazd_vin', 'opis', 'data_serwisu', 'koszt', 'typ_zdarzenia']


class ReservationFileDto(serializers.ModelSerializer):
    class Meta:
        model = ReservationFile
        fields = ['id', 'file', 'uploaded_at']

# 7. REZERWACJE (NOWE)
class ReservationDto(serializers.ModelSerializer):
    assigned_vehicle_display = serializers.ReadOnlyField(source='assigned_vehicle.registration_number')

    driver_display = serializers.SerializerMethodField()

    # DO ODCZYTU: Lista już wgranych plików
    attachments = ReservationFileDto(many=True, read_only=True)

    # DO ZAPISU: Lista nowych plików (ListField z FileField)
    new_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    # DO USUWANIA: Lista ID plików do usunięcia
    remove_attachment_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Reservation
        fields = [
            'id', 'first_name', 'last_name', 'company',
            'date_from', 'date_to', 'vehicle_type', 'status',
            'created_at', 'assigned_vehicle', 'assigned_vehicle_display',
            'additional_info', 'attachments', 'new_files', 'remove_attachment_ids',
            'driver', 'driver_display'
        ]

    def get_driver_display(self, obj):
        if obj.driver and obj.driver.user:
            return f"{obj.driver.user.first_name} {obj.driver.user.last_name}"
        return None

    def create(self, validated_data):
        new_files = validated_data.pop('new_files', [])
        validated_data.pop('remove_attachment_ids', [])  # Przy tworzeniu nie usuwamy

        reservation = Reservation.objects.create(**validated_data)

        # Tworzymy obiekty plików
        for file in new_files:
            ReservationFile.objects.create(reservation=reservation, file=file)

        return reservation

    def update(self, instance, validated_data):
        new_files = validated_data.pop('new_files', [])
        remove_ids = validated_data.pop('remove_attachment_ids', [])

        # 1. Usuwanie wskazanych plików
        if remove_ids:
            # Filtrujemy, żeby usunąć tylko pliki należące do tej rezerwacji
            files_to_delete = ReservationFile.objects.filter(
                id__in=remove_ids,
                reservation=instance
            )
            for f in files_to_delete:
                f.file.delete(save=False)  # Usuń fizyczny plik z dysku
                f.delete()  # Usuń wpis z bazy

        # 2. Dodawanie nowych plików
        for file in new_files:
            ReservationFile.objects.create(reservation=instance, file=file)

        # 3. Standardowa aktualizacja reszty pól
        return super().update(instance, validated_data)


class VehicleDocumentDto(serializers.ModelSerializer):
    vehicle_reg = serializers.ReadOnlyField(source='vehicle.registration_number')

    class Meta:
        model = VehicleDocument
        fields = ['id', 'vehicle', 'vehicle_reg', 'title', 'file', 'uploaded_at', 'description']

class GlobalSettingsDto(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        fields = '__all__'

