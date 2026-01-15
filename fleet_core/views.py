# Master/Server/fleet_core/views.py

from rest_framework import viewsets, permissions
# Importy dla tokenów JWT i API
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate  # Do weryfikacji hasła
from rest_framework_simplejwt.tokens import RefreshToken  # Do generowania tokenów
from django.shortcuts import render
from django.db.models import Q  # <--- WAŻNE: Potrzebne do filtrowania w my_list

# Importy Serializerów
from .serializers import (
    VehicleDto, DriverDto, DamageEventDto, InsurancePolicyDto,
    VehicleHandoverDto, ServiceEventDto, ReservationDto,
    VehicleDocumentDto, GlobalSettingsDto
)

# Importy Modeli
from .models import (
    Vehicle, Driver, DamageEvent, InsurancePolicy, CustomUser,
    VehicleHandover, ServiceEvent, Reservation, VehicleDocument,
    GlobalSettings, FleetCompany
)


# ----------------------------------------------------
# WIDOKI DLA ZARZĄDZANIA DANYMI FLOTY (Fleet Data ViewSets)
# ----------------------------------------------------

# 1. WIDOK DLA POJAZDÓW
class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleDto
    # queryset usuwamy z atrybutów klasy, bo jest dynamiczny w get_queryset

    def get_queryset(self):
        """
        Nadpisujemy standardowe zapytanie, aby filtrować dane w zależności od roli.
        """
        user = self.request.user

        # Podstawowe zapytanie: pobierz wszystkie auta + firmę
        queryset = Vehicle.objects.select_related('company').all()

        # JEŚLI to Kierowca lub Pracownik -> filtrujemy widoczność
        if user.is_authenticated and user.rola in ['DRIVER', 'USER']:
            # 1. Pobieramy ID aut, które użytkownik ma aktualnie (niezwrócone przekazania)
            current_handover_ids = VehicleHandover.objects.filter(
                kierowca__user=user,
                data_zwrotu__isnull=True
            ).values_list('pojazd_id', flat=True)

            # 2. Zwracamy auta: Przypisane na stałe (assigned_user) LUB aktualnie wypożyczone
            queryset = queryset.filter(
                Q(assigned_user=user) | Q(id__in=current_handover_ids)
            ).distinct()

        return queryset

    # --- NOWA METODA DLA APLIKACJI MOBILNEJ (MOJE POJAZDY) ---
    @action(detail=False, methods=['get'])
    def my_list(self, request):
        """
        Zwraca tylko pojazdy przypisane do zalogowanego użytkownika (stałe lub przez wydanie).
        """
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Wymagane logowanie"}, status=401)

        # 1. Pobieramy ID aut z aktywnych przekazań tego kierowcy (niezwrócone)
        active_handovers_ids = VehicleHandover.objects.filter(
            kierowca__user=user,
            data_zwrotu__isnull=True
        ).values_list('pojazd_id', flat=True)

        # 2. Filtrujemy: Auto przypisane na stałe LUB auto z aktywnego wydania
        vehicles = Vehicle.objects.filter(
            Q(assigned_user=user) | Q(id__in=active_handovers_ids)
        ).distinct()

        serializer = self.get_serializer(vehicles, many=True)
        return Response(serializer.data)

    # --- HISTORIA POJAZDU ---
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        vehicle = self.get_object()
        events = []

        # 1. Przekazania (HANDOVER)
        for h in vehicle.handovers.all():
            kierowca = f"{h.kierowca.user.first_name} {h.kierowca.user.last_name}"
            firma = h.kierowca.company.nazwa if h.kierowca.company else 'Brak firmy'

            # Opis Wydania
            desc_start = f"Kierowca: {kierowca} ({firma})."
            desc_start += f"\nStan licznika: {h.przebieg_start} km."
            desc_start += f" Paliwo: {h.paliwo_start}%."
            if h.uwagi:
                desc_start += f"\nUwagi: {h.uwagi}"

            events.append({
                'date': h.data_wydania,
                'type': 'HANDOVER',
                'title': 'Wydanie Pojazdu',
                'description': desc_start,
                'icon': 'fa-key',
                'color': '#0d47a1'
            })

            # Opis Zwrotu
            if h.data_zwrotu:
                desc_stop = f"Zwrot od: {kierowca}."
                desc_stop += f"\nStan licznika: {h.przebieg_stop} km."
                desc_stop += f" Paliwo: {h.paliwo_stop}%."

                if h.calkowity_koszt and float(h.calkowity_koszt) > 0:
                    desc_stop += f"\nRozliczenie: {h.calkowity_koszt} PLN."

                events.append({
                    'date': h.data_zwrotu,
                    'type': 'RETURN',
                    'title': 'Zwrot Pojazdu',
                    'description': desc_stop,
                    'icon': 'fa-check-circle',
                    'color': '#17a2b8'
                })

        # 2. Szkody
        for d in vehicle.damage_history.all():
            szkoda_desc = d.opis
            if d.szacowany_koszt and float(d.szacowany_koszt) > 0:
                szkoda_desc += f"\nSzacowany koszt: {d.szacowany_koszt} PLN"

            events.append({
                'date': d.data_zdarzenia,
                'type': 'DAMAGE',
                'title': f'Szkoda ({d.get_status_naprawy_display()})',
                'description': szkoda_desc,
                'icon': 'fa-car-burst',
                'color': '#8B0000'
            })

        # 3. Serwisy
        for s in vehicle.service_history.all():
            service_desc = s.opis
            if s.koszt and float(s.koszt) > 0:
                service_desc += f"\nKoszt: {s.koszt} PLN"

            if s.typ_zdarzenia == 'PRZEGLAD':
                color = '#28a745'
                icon = 'fa-check-double'
            elif s.typ_zdarzenia == 'NAPRAWA':
                color = '#dc3545'
                icon = 'fa-tools'
            elif s.typ_zdarzenia == 'BADANIE_TECH':
                color = '#ffc107'
                icon = 'fa-clipboard-check'
            else:
                color = '#6c757d'
                icon = 'fa-wrench'

            events.append({
                'date': s.data_serwisu,
                'type': 'SERVICE',
                'title': f"{s.get_typ_zdarzenia_display()}",
                'description': service_desc,
                'icon': icon,
                'color': color
            })

        # 4. Polisy
        for p in vehicle.policies.all():
            policy_desc = f"Ubezpieczyciel: {p.ubezpieczyciel}\nNr: {p.numer_polisy}"
            if p.koszt and float(p.koszt) > 0:
                policy_desc += f"\nKoszt: {p.koszt} PLN"

            events.append({
                'date': p.data_waznosci_oc,
                'type': 'POLICY',
                'title': f"Koniec Polisy OC",
                'description': policy_desc,
                'icon': 'fa-file-contract',
                'color': '#007bff'
            })

            if p.data_waznosci_ac:
                events.append({
                    'date': p.data_waznosci_ac,
                    'type': 'POLICY',
                    'title': f"Koniec Polisy AC",
                    'description': policy_desc,
                    'icon': 'fa-shield-alt',
                    'color': '#007bff'
                })

        events.sort(key=lambda x: str(x['date']), reverse=True)
        return Response(events)

    # --- DOSTĘPNOŚĆ (TERMINARZ) ---
    @action(detail=False, methods=['get'])
    def availability(self, request):
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')
        exclude_id = request.query_params.get('exclude_id')

        vehicles = self.get_queryset()
        data = []

        if not start_date or not end_date:
            for v in vehicles:
                data.append({
                    'id': v.id,
                    'registration_number': v.registration_number,
                    'marka': v.marka,
                    'model': v.model,
                    'status': v.status,
                    'is_available': True,
                    'busy_info': ''
                })
            return Response(data)

        for v in vehicles:
            conflicts = Reservation.objects.filter(
                assigned_vehicle=v,
                date_from__lte=end_date,
                date_to__gte=start_date
            ).exclude(status='ODRZUCONE')

            if exclude_id:
                conflicts = conflicts.exclude(id=exclude_id)

            is_busy = conflicts.exists()
            busy_info = ""
            if is_busy:
                c = conflicts.first()
                busy_info = f"Zajęty: {c.date_from} - {c.date_to}"

            data.append({
                'id': v.id,
                'registration_number': v.registration_number,
                'marka': v.marka,
                'model': v.model,
                'status': v.status,
                'is_available': not is_busy,
                'busy_info': busy_info
            })

        return Response(data)


# 2. WIDOK DLA UŻYTKOWNIKÓW (Kierowców)
class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.select_related('user').all()
    serializer_class = DriverDto


# 3. WIDOK DLA ZDARZEŃ SERWISOWYCH (POPRAWIONE FILTROWANIE)
class ServiceEventViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceEventDto

    def get_queryset(self):
        user = self.request.user
        queryset = ServiceEvent.objects.select_related('pojazd').all().order_by('-data_serwisu')

        if user.is_authenticated and user.rola in ['DRIVER', 'USER']:
            current_handover_ids = VehicleHandover.objects.filter(
                kierowca__user=user,
                data_zwrotu__isnull=True
            ).values_list('pojazd_id', flat=True)

            queryset = queryset.filter(
                Q(pojazd__assigned_user=user) | Q(pojazd__id__in=current_handover_ids)
            ).distinct()

        vehicle_id = self.request.query_params.get('vehicle')
        if vehicle_id:
            queryset = queryset.filter(pojazd_id=vehicle_id)

        return queryset


# 4. WIDOK DLA ZDARZEŃ SZKODOWYCH
class DamageEventViewSet(viewsets.ModelViewSet):
    serializer_class = DamageEventDto

    def get_queryset(self):
        user = self.request.user
        queryset = DamageEvent.objects.select_related('pojazd').all().order_by('-data_zdarzenia')

        if user.is_authenticated and user.rola in ['DRIVER', 'USER']:
            current_handover_ids = VehicleHandover.objects.filter(
                kierowca__user=user,
                data_zwrotu__isnull=True
            ).values_list('pojazd_id', flat=True)

            queryset = queryset.filter(
                Q(pojazd__assigned_user=user) | Q(pojazd__id__in=current_handover_ids)
            ).distinct()

        vehicle_id = self.request.query_params.get('vehicle')
        if vehicle_id:
            queryset = queryset.filter(pojazd_id=vehicle_id)

        return queryset

    def _update_vehicle_status(self, vehicle):
        ma_aktywne_szkody = DamageEvent.objects.filter(
            pojazd=vehicle,
            status_naprawy__in=['ZGLOSZONA', 'W_NAPRAWIE']
        ).exists()

        if ma_aktywne_szkody:
            vehicle.status = 'NIESPRAWNY'
        else:
            vehicle.status = 'SPRAWNY'
        vehicle.save()

    def perform_create(self, serializer):
        damage = serializer.save()
        self._update_vehicle_status(damage.pojazd)

    def perform_update(self, serializer):
        damage = serializer.save()
        self._update_vehicle_status(damage.pojazd)

    def perform_destroy(self, instance):
        vehicle = instance.pojazd
        instance.delete()
        self._update_vehicle_status(vehicle)


# 5. WIDOK DLA POLIS (POPRAWIONE FILTROWANIE)
class InsurancePolicyViewSet(viewsets.ModelViewSet):
    serializer_class = InsurancePolicyDto

    def get_queryset(self):
        user = self.request.user
        queryset = InsurancePolicy.objects.select_related('pojazd').all()

        if user.is_authenticated and user.rola in ['DRIVER', 'USER']:
            current_handover_ids = VehicleHandover.objects.filter(
                kierowca__user=user,
                data_zwrotu__isnull=True
            ).values_list('pojazd_id', flat=True)

            queryset = queryset.filter(
                Q(pojazd__assigned_user=user) | Q(pojazd__id__in=current_handover_ids)
            ).distinct()

        vehicle_id = self.request.query_params.get('vehicle')
        if vehicle_id:
            queryset = queryset.filter(pojazd_id=vehicle_id)

        return queryset


# 6. WIDOK DLA PRZEKAZAŃ
class VehicleHandoverViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleHandoverDto
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        queryset = VehicleHandover.objects.select_related('kierowca__user', 'kierowca__company', 'pojazd').all().order_by('-data_wydania')

        if user.is_authenticated and user.rola in ['DRIVER', 'USER']:
            queryset = queryset.filter(kierowca__user=user)

        vehicle_id = self.request.query_params.get('vehicle')
        if vehicle_id:
            queryset = queryset.filter(pojazd_id=vehicle_id)

        return queryset


# 7. WIDOK DLA REZERWACJI
class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationDto

    def get_queryset(self):
        user = self.request.user
        queryset = Reservation.objects.all().order_by('-created_at')

        if user.is_authenticated and user.rola in ['DRIVER', 'USER']:
            try:
                driver_profile = Driver.objects.get(user=user)
                queryset = queryset.filter(driver=driver_profile)
            except Driver.DoesNotExist:
                return Reservation.objects.none()

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.rola in ['DRIVER', 'USER']:
            try:
                driver_profile = Driver.objects.get(user=user)
                serializer.save(
                    driver=driver_profile,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    company=driver_profile.company.nazwa if driver_profile.company else ''
                )
            except Driver.DoesNotExist:
                serializer.save()
        else:
            serializer.save()

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.status == 'ZATWIERDZONE' and instance.assigned_vehicle and instance.driver:
            exists = VehicleHandover.objects.filter(
                pojazd=instance.assigned_vehicle,
                data_wydania=instance.date_from
            ).exists()

            if not exists:
                VehicleHandover.objects.create(
                    kierowca=instance.driver,
                    pojazd=instance.assigned_vehicle,
                    reservation=instance,
                    data_wydania=instance.date_from,
                    data_zwrotu=instance.date_to,
                    uwagi=f"Automatycznie z rezerwacji (ID: {instance.id})."
                )


# 8. WIDOK DLA DOKUMENTÓW I USTAWIEŃ
class VehicleDocumentViewSet(viewsets.ModelViewSet):
    queryset = VehicleDocument.objects.select_related('vehicle').all().order_by('-uploaded_at')
    serializer_class = VehicleDocumentDto

    def get_queryset(self):
        queryset = super().get_queryset()
        vehicle_id = self.request.query_params.get('vehicle')
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
        return queryset


class GlobalSettingsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        settings_obj, created = GlobalSettings.objects.get_or_create(id=1)
        serializer = GlobalSettingsDto(settings_obj)
        return Response(serializer.data)

    def create(self, request):
        settings_obj, created = GlobalSettings.objects.get_or_create(id=1)
        serializer = GlobalSettingsDto(settings_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


# ----------------------------------------------------
# WIDOKI FUNKCYJNE (LOGIN, REJESTRACJA, MOBILE)
# ----------------------------------------------------

@api_view(['POST'])
@permission_classes([])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    pin_2fa = request.data.get('pin_2fa')

    user = authenticate(username=username, password=password)

    if user is not None:
        if user.rola == 'ADMIN':
            if not pin_2fa or user.pin_2fa != pin_2fa:
                return Response(
                    {'detail': 'Błąd 2FA. Wymagane hasło i poprawny PIN 2FA dla Administratora.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_role': user.rola,
            'username': user.username
        }, status=status.HTTP_200_OK)

    return Response(
        {'detail': 'Nieprawidłowa nazwa użytkownika lub hasło.'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([])
def register_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    company_name = request.data.get('company_name', '').strip()
    rola = 'DRIVER'
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')

    if not username or not password:
        return Response({'detail': 'Nazwa użytkownika i hasło są wymagane.'}, status=status.HTTP_400_BAD_REQUEST)

    if not company_name:
        return Response({'detail': 'Podanie nazwy firmy jest wymagane.'}, status=status.HTTP_400_BAD_REQUEST)

    if CustomUser.objects.filter(username=username).exists():
        return Response({'detail': 'Użytkownik o tej nazwie już istnieje.'}, status=status.HTTP_400_BAD_REQUEST)

    user = CustomUser.objects.create_user(
        username=username,
        password=password,
        email=email,
        rola=rola,
        first_name=first_name,
        last_name=last_name
    )

    company_obj, created = FleetCompany.objects.get_or_create(
        nazwa=company_name,
        defaults={'nip': ''}
    )

    Driver.objects.create(
        user=user,
        company=company_obj,
        numer_prawa_jazdy="",
        kategorie_prawa_jazdy="B"
    )

    return Response({'detail': 'Konto zostało utworzone. Możesz się zalogować.'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([])
def mobile_app_view(request):
    return render(request, 'mobile.html')