# Master/Server/fleet_core/serializers.py

from rest_framework import serializers
from django.db.models import Q
import datetime
from .models import Vehicle, Driver, ServiceEvent, DamageEvent, FleetCompany, InsurancePolicy, VehicleHandover, \
    Reservation, ReservationFile, VehicleDocument, GlobalSettings


# 1. SERIALIZER DLA POJAZDÓW
class VehicleDto(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.nazwa', read_only=True)
    fuel_type_display = serializers.CharField(source='get_fuel_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    typ_display = serializers.CharField(source='get_typ_pojazdu_display', read_only=True)

    assigned_user_name = serializers.SerializerMethodField()

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
            'scan_registration_card', 'scan_policy_oc', 'scan_policy_ac',
            'scan_tech_inspection', 'scan_service_book', 'scan_purchase_invoice',
            'remove_scan_registration_card', 'remove_scan_policy_oc',
            'remove_scan_policy_ac', 'remove_scan_tech_inspection',
            'remove_scan_service_book', 'remove_scan_purchase_invoice'
        ]

    def get_assigned_user_name(self, obj):
        """
        Sprawdza:
        1. Aktywne wydanie (Handover).
        2. Aktywną Rezerwację (data OD <= dzisiaj <= data DO).
        3. Stałe przypisanie.
        """
        today = datetime.date.today()
        user = None
        info = ""

        # 1. Sprawdź Handover (Fizyczne wydanie)
        active_handover = VehicleHandover.objects.filter(
            pojazd=obj,
            data_zwrotu__isnull=True
        ).order_by('-data_wydania').first()

        if active_handover and active_handover.kierowca and active_handover.kierowca.user:
            user = active_handover.kierowca.user

        # 2. Jeśli nie ma wydania, sprawdź REZERWACJE (zgodnie z Twoim życzeniem)
        if not user:
            # Szukamy rezerwacji na dzisiaj
            active_res = Reservation.objects.filter(
                assigned_vehicle=obj,
                status__in=['ZATWIERDZONE', 'PRZYJETE', 'OCZEKUJACE'],
                date_from__lte=today,
                date_to__gte=today
            ).exclude(status='ODRZUCONE').first()

            if active_res:
                if active_res.first_name and active_res.last_name:
                    return f"{active_res.first_name} {active_res.last_name}"
                elif active_res.driver and active_res.driver.user:
                    user = active_res.driver.user
                    info = "(Rez.)"

        # 3. Stałe przypisanie
        if not user:
            user = obj.assigned_user

        if user:
            name = f"{user.first_name} {user.last_name}".strip()
            if name: return f"{name} {info}".strip()
            return f"{user.username} {info}".strip()

        return "-"

    def create(self, validated_data):
        validated_data.pop('remove_scan_registration_card', None)
        validated_data.pop('remove_scan_policy_oc', None)
        validated_data.pop('remove_scan_policy_ac', None)
        validated_data.pop('remove_scan_tech_inspection', None)
        validated_data.pop('remove_scan_service_book', None)
        validated_data.pop('remove_scan_purchase_invoice', None)
        return super().create(validated_data)

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
            if validated_data.pop(remove_flag, False):
                file_field = getattr(instance, field_name)
                if file_field:
                    file_field.delete(save=False)
                    setattr(instance, field_name, None)
        return super().update(instance, validated_data)


# POZOSTAŁE SERIALIZERY POZOSTAJĄ TAKIE SAME JAK POPRZEDNIO
# (Skopiuj resztę klas: DriverDto, DamageEventDto itd. z poprzedniego pliku, bo tam są OK)
class DriverDto(serializers.ModelSerializer):
    first_name = serializers.ReadOnlyField(source='user.first_name', default='')
    last_name = serializers.ReadOnlyField(source='user.last_name', default='')
    user_name = serializers.ReadOnlyField(source='user.username', default='Brak loginu')
    email = serializers.ReadOnlyField(source='user.email', default='Brak email')
    company_name = serializers.CharField(source='company.nazwa', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = ['id', 'user', 'user_name', 'first_name', 'last_name', 'full_name', 'email', 'numer_prawa_jazdy',
                  'kategorie_prawa_jazdy', 'data_waznosci_prawa_jazdy', 'data_waznosci_badan', 'company',
                  'company_name']

    def get_full_name(self, obj):
        if obj.user: return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
        return "Nieznany"


class DamageEventDto(serializers.ModelSerializer):
    pojazd_rej = serializers.CharField(source='pojazd.registration_number', read_only=True)
    pojazd_marka = serializers.ReadOnlyField(source='pojazd.marka')
    pojazd_model = serializers.ReadOnlyField(source='pojazd.model')
    status_display = serializers.CharField(source='get_status_naprawy_display', read_only=True)
    has_photos = serializers.SerializerMethodField()

    class Meta:
        model = DamageEvent
        fields = ['id', 'pojazd', 'pojazd_rej', 'pojazd_marka', 'pojazd_model', 'opis', 'data_zdarzenia',
                  'szacowany_koszt', 'zgloszony_do_ubezpieczyciela', 'status_naprawy', 'status_display', 'has_photos']

    def get_has_photos(self, obj):
        return VehicleDocument.objects.filter(vehicle=obj.pojazd, title__icontains='SZKODA',
                                              uploaded_at__date=obj.data_zdarzenia).exists()


class InsurancePolicyDto(serializers.ModelSerializer):
    pojazd_nr_rej = serializers.CharField(source='pojazd.registration_number', read_only=True)
    pojazd_vin = serializers.ReadOnlyField(source='pojazd.vin')

    class Meta:
        model = InsurancePolicy
        fields = ['id', 'pojazd', 'pojazd_nr_rej', 'pojazd_vin', 'numer_polisy', 'ubezpieczyciel', 'data_waznosci_oc',
                  'data_waznosci_ac', 'koszt']


class VehicleHandoverDto(serializers.ModelSerializer):
    imie = serializers.ReadOnlyField(source='kierowca.user.first_name')
    nazwisko = serializers.ReadOnlyField(source='kierowca.user.last_name')
    firma = serializers.ReadOnlyField(source='kierowca.company.nazwa')
    marka = serializers.ReadOnlyField(source='pojazd.marka')
    model = serializers.ReadOnlyField(source='pojazd.model')
    rejestracja = serializers.ReadOnlyField(source='pojazd.registration_number')
    reservation_id = serializers.ReadOnlyField(source='reservation.id')
    remove_scan_agreement = serializers.BooleanField(write_only=True, required=False)
    remove_scan_handover_protocol = serializers.BooleanField(write_only=True, required=False)
    remove_scan_return_protocol = serializers.BooleanField(write_only=True, required=False)
    dystans = serializers.SerializerMethodField()

    class Meta:
        model = VehicleHandover
        fields = ['id', 'kierowca', 'pojazd', 'reservation_id', 'imie', 'nazwisko', 'firma', 'marka', 'model',
                  'rejestracja', 'data_wydania', 'data_zwrotu', 'uwagi', 'przebieg_start', 'przebieg_stop', 'dystans',
                  'paliwo_start', 'paliwo_stop', 'stawka_za_km', 'koszt_brakujacego_paliwa', 'calkowity_koszt',
                  'scan_agreement', 'scan_handover_protocol', 'scan_return_protocol', 'remove_scan_agreement',
                  'remove_scan_handover_protocol', 'remove_scan_return_protocol']

    def get_dystans(self, obj):
        if obj.przebieg_stop and obj.przebieg_start: return obj.przebieg_stop - obj.przebieg_start
        return 0

    def create(self, validated_data):
        validated_data.pop('remove_scan_agreement', None)
        validated_data.pop('remove_scan_handover_protocol', None)
        validated_data.pop('remove_scan_return_protocol', None)
        handover = VehicleHandover.objects.create(**validated_data)
        if not handover.data_zwrotu:
            vehicle = handover.pojazd
            vehicle.assigned_user = handover.kierowca.user
            vehicle.status = 'WYPOZYCZONY'
            vehicle.save()
        return handover

    def update(self, instance, validated_data):
        files_to_check = [('scan_agreement', 'remove_scan_agreement'),
                          ('scan_handover_protocol', 'remove_scan_handover_protocol'),
                          ('scan_return_protocol', 'remove_scan_return_protocol')]
        for field, flag in files_to_check:
            if validated_data.pop(flag, False):
                f = getattr(instance, field)
                if f:
                    f.delete(save=False)
                    setattr(instance, field, None)
        instance = super().update(instance, validated_data)
        if instance.data_zwrotu:
            vehicle = instance.pojazd
            if vehicle.assigned_user == instance.kierowca.user:
                vehicle.assigned_user = None
                vehicle.status = 'SPRAWNY'
            if instance.przebieg_stop: vehicle.przebieg = instance.przebieg_stop
            vehicle.save()
        return instance


class ServiceEventDto(serializers.ModelSerializer):
    pojazd_nr_rej = serializers.ReadOnlyField(source='pojazd.registration_number')
    pojazd_vin = serializers.ReadOnlyField(source='pojazd.vin')

    class Meta:
        model = ServiceEvent
        fields = ['id', 'pojazd', 'pojazd_nr_rej', 'pojazd_vin', 'opis', 'data_serwisu', 'koszt', 'typ_zdarzenia']


class ReservationFileDto(serializers.ModelSerializer):
    class Meta:
        model = ReservationFile
        fields = ['id', 'file', 'uploaded_at']


class ReservationDto(serializers.ModelSerializer):
    assigned_vehicle_display = serializers.ReadOnlyField(source='assigned_vehicle.registration_number')
    driver_display = serializers.SerializerMethodField()
    attachments = ReservationFileDto(many=True, read_only=True)
    new_files = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    remove_attachment_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = Reservation
        fields = ['id', 'first_name', 'last_name', 'company', 'date_from', 'date_to', 'vehicle_type', 'status',
                  'created_at', 'assigned_vehicle', 'assigned_vehicle_display', 'additional_info', 'attachments',
                  'new_files', 'remove_attachment_ids', 'driver', 'driver_display']

    def get_driver_display(self, obj):
        if obj.driver and obj.driver.user: return f"{obj.driver.user.first_name} {obj.driver.user.last_name}"
        return None

    def create(self, validated_data):
        new_files = validated_data.pop('new_files', [])
        validated_data.pop('remove_attachment_ids', [])
        reservation = Reservation.objects.create(**validated_data)
        for file in new_files: ReservationFile.objects.create(reservation=reservation, file=file)
        return reservation

    def update(self, instance, validated_data):
        new_files = validated_data.pop('new_files', [])
        remove_ids = validated_data.pop('remove_attachment_ids', [])
        if remove_ids:
            files_to_delete = ReservationFile.objects.filter(id__in=remove_ids, reservation=instance)
            for f in files_to_delete:
                f.file.delete(save=False)
                f.delete()
        for file in new_files: ReservationFile.objects.create(reservation=instance, file=file)
        return super().update(instance, validated_data)

    def validate(self, data):
        assigned_vehicle = data.get('assigned_vehicle')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        if self.instance:
            if not assigned_vehicle: assigned_vehicle = self.instance.assigned_vehicle
            if not date_from: date_from = self.instance.date_from
            if not date_to: date_to = self.instance.date_to
        if date_from and date_to and date_from > date_to: raise serializers.ValidationError(
            "Data 'Do' nie może być wcześniejsza niż data 'Od'.")
        if assigned_vehicle:
            conflicts = Reservation.objects.filter(assigned_vehicle=assigned_vehicle, date_from__lte=date_to,
                                                   date_to__gte=date_from).exclude(status='ODRZUCONE')
            if self.instance: conflicts = conflicts.exclude(id=self.instance.id)
            if conflicts.exists():
                collision = conflicts.first()
                msg = f"Pojazd {assigned_vehicle.registration_number} jest już zajęty ({collision.date_from} - {collision.date_to})."
                raise serializers.ValidationError(msg)
        return data


class VehicleDocumentDto(serializers.ModelSerializer):
    vehicle_reg = serializers.ReadOnlyField(source='vehicle.registration_number')

    class Meta:
        model = VehicleDocument
        fields = ['id', 'vehicle', 'vehicle_reg', 'title', 'file', 'uploaded_at', 'description']


class GlobalSettingsDto(serializers.ModelSerializer):
    class Meta:
        model = GlobalSettings
        fields = '__all__'