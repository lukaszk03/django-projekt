# Master/Server/fleet_core/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import render
from django.db.models import Q
import datetime

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


# --- FUNKCJA 1: Tylko AKTUALNE auta (Dla zakładki "Pojazdy") ---
def get_driver_vehicle_ids(user):
    """
    Zwraca ID pojazdów, które kierowca ma TERAZ (Rezerwacja trwa, lub Wydanie jest otwarte).
    """
    today = datetime.date.today()
    vehicle_ids = set()

    # 1. Przypisane na stałe
    assigned = Vehicle.objects.filter(assigned_user=user).values_list('id', flat=True)
    vehicle_ids.update(assigned)

    # 2. Aktywne rezerwacje (Dziś mieści się w dacie)
    reserved = Reservation.objects.filter(
        driver__user=user,
        status__in=['ZATWIERDZONE', 'PRZYJETE', 'OCZEKUJACE'],
        date_from__lte=today,
        date_to__gte=today
    ).values_list('assigned_vehicle_id', flat=True)
    vehicle_ids.update(reserved)

    # 3. Aktywne wydania (Brak daty zwrotu lub zwrot w przyszłości)
    handed_over = VehicleHandover.objects.filter(
        kierowca__user=user
    ).filter(
        Q(data_zwrotu__isnull=True) | Q(data_zwrotu__gte=today)
    ).values_list('pojazd_id', flat=True)
    vehicle_ids.update(handed_over)

    return list(vehicle_ids)


# --- FUNKCJA 2: CAŁA HISTORIA aut (Dla zakładki "Szkody") ---
def get_all_history_vehicle_ids(user):
    """
    Zwraca ID wszystkich pojazdów, z którymi kierowca miał kiedykolwiek styczność.
    Dzięki temu widzi szkody nawet po oddaniu auta.
    """
    vehicle_ids = set()

    # 1. Aktualne (te co wyżej)
    vehicle_ids.update(get_driver_vehicle_ids(user))

    # 2. Stare/Zakończone rezerwacje
    past_reservations = Reservation.objects.filter(
        driver__user=user
    ).values_list('assigned_vehicle_id', flat=True)
    vehicle_ids.update(past_reservations)

    # 3. Zakończone wydania (Auta oddane)
    past_handovers = VehicleHandover.objects.filter(
        kierowca__user=user
    ).values_list('pojazd_id', flat=True)
    vehicle_ids.update(past_handovers)

    return list(vehicle_ids)


# 1. WIDOK DLA POJAZDÓW
class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleDto

    def get_queryset(self):
        user = self.request.user
        queryset = Vehicle.objects.select_related('company').all()

        if not user.is_authenticated:
            return Vehicle.objects.none()

        # Kierowca widzi tylko auta, które ma TERAZ
        if hasattr(user, 'rola') and user.rola == 'DRIVER':
            my_ids = get_driver_vehicle_ids(user)
            queryset = queryset.filter(id__in=my_ids)

        return queryset

    # Metoda dla aplikacji mobilnej
    @action(detail=False, methods=['get'])
    def my_list(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Wymagane logowanie"}, status=401)

        my_ids = get_driver_vehicle_ids(user)
        vehicles = Vehicle.objects.filter(id__in=my_ids)
        serializer = self.get_serializer(vehicles, many=True)
        return Response(serializer.data)

    # Historia pojazdu
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        vehicle = self.get_object()
        events = []
        for h in vehicle.handovers.all():
            kierowca_str = "Nieznany"
            if h.kierowca and h.kierowca.user:
                kierowca_str = f"{h.kierowca.user.first_name} {h.kierowca.user.last_name}"
            events.append({
                'date': h.data_wydania, 'type': 'HANDOVER',
                'title': 'Wydanie', 'description': f"Kierowca: {kierowca_str}",
                'icon': 'fa-key', 'color': '#0d47a1'
            })
            if h.data_zwrotu:
                events.append({
                    'date': h.data_zwrotu, 'type': 'RETURN',
                    'title': 'Zwrot', 'description': f"Zwrot od: {kierowca_str}",
                    'icon': 'fa-check-circle', 'color': '#17a2b8'
                })
        for d in vehicle.damage_history.all():
            events.append({
                'date': d.data_zdarzenia, 'type': 'DAMAGE',
                'title': 'Szkoda', 'description': d.opis,
                'icon': 'fa-car-burst', 'color': '#8B0000'
            })
        for s in vehicle.service_history.all():
            events.append({
                'date': s.data_serwisu, 'type': 'SERVICE',
                'title': s.get_typ_zdarzenia_display(), 'description': s.opis,
                'icon': 'fa-wrench', 'color': '#6c757d'
            })
        for p in vehicle.policies.all():
            events.append({
                'date': p.data_waznosci_oc, 'type': 'POLICY',
                'title': 'Polisa OC', 'description': p.ubezpieczyciel,
                'icon': 'fa-file-contract', 'color': '#007bff'
            })
        events.sort(key=lambda x: str(x['date']), reverse=True)
        return Response(events)

    @action(detail=False, methods=['get'])
    def availability(self, request):
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')
        exclude_id = request.query_params.get('exclude_id')
        vehicles = self.get_queryset()
        data = []
        if not start_date or not end_date:
            for v in vehicles:
                data.append(
                    {'id': v.id, 'registration_number': v.registration_number, 'marka': v.marka, 'model': v.model,
                     'status': v.status, 'is_available': True, 'busy_info': ''})
            return Response(data)
        for v in vehicles:
            conflicts = Reservation.objects.filter(assigned_vehicle=v, date_from__lte=end_date,
                                                   date_to__gte=start_date).exclude(status='ODRZUCONE')
            if exclude_id: conflicts = conflicts.exclude(id=exclude_id)
            is_busy = conflicts.exists()
            busy_info = f"Zajęty: {conflicts.first().date_from} - {conflicts.first().date_to}" if is_busy else ""
            data.append({'id': v.id, 'registration_number': v.registration_number, 'marka': v.marka, 'model': v.model,
                         'status': v.status, 'is_available': not is_busy, 'busy_info': busy_info})
        return Response(data)


# 2. WIDOK SZKÓD
class DamageEventViewSet(viewsets.ModelViewSet):
    serializer_class = DamageEventDto

    def get_queryset(self):
        user = self.request.user
        queryset = DamageEvent.objects.all().order_by('-data_zdarzenia')

        if user.is_authenticated and hasattr(user, 'rola') and user.rola == 'DRIVER':
            history_ids = get_all_history_vehicle_ids(user)
            queryset = queryset.filter(pojazd_id__in=history_ids)

        return queryset


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverDto


class InsurancePolicyViewSet(viewsets.ModelViewSet):
    queryset = InsurancePolicy.objects.all()
    serializer_class = InsurancePolicyDto


class VehicleHandoverViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleHandoverDto
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user = self.request.user
        queryset = VehicleHandover.objects.select_related('kierowca__user', 'kierowca__company',
                                                          'pojazd').all().order_by('-data_wydania')
        if user.is_authenticated and hasattr(user, 'rola') and user.rola in ['DRIVER', 'USER']:
            queryset = queryset.filter(kierowca__user=user)
        vehicle_id = self.request.query_params.get('vehicle')
        if vehicle_id:
            queryset = queryset.filter(pojazd_id=vehicle_id)
        return queryset

    def perform_create(self, serializer):
        handover = serializer.save()
        vehicle = handover.pojazd
        if handover.data_zwrotu:
            if vehicle.assigned_user == handover.kierowca.user:
                vehicle.assigned_user = None
                vehicle.status = 'SPRAWNY'
        else:
            if handover.kierowca and handover.kierowca.user:
                vehicle.assigned_user = handover.kierowca.user
                vehicle.status = 'WYPOZYCZONY'
        vehicle.save()


class ServiceEventViewSet(viewsets.ModelViewSet):
    queryset = ServiceEvent.objects.all()
    serializer_class = ServiceEventDto


# --- ULEPSZONA KLASA REZERWACJI ---
class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationDto

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'rola') and user.rola == 'DRIVER':
            return Reservation.objects.filter(driver__user=user)
        return Reservation.objects.all().order_by('-created_at')

    def _create_handover_if_approved(self, instance):
        """Wspólna logika dla create i update z dokładnymi logami"""
        print(f"--- DEBUG REZERWACJI ID={instance.id} ---")
        print(f"Status: {instance.status}")
        print(f"Pojazd: {instance.assigned_vehicle}")
        print(f"Kierowca: {instance.driver}")

        # 1. Sprawdzenie statusu
        if instance.status != 'ZATWIERDZONE':
            print("DEBUG: Status nie jest ZATWIERDZONE. Pomijam tworzenie przekazania.")
            return

        # 2. Sprawdzenie danych
        if not instance.assigned_vehicle:
            print("DEBUG: BŁĄD - Brak przypisanego POJAZDU! Przekazanie nie zostanie utworzone.")
            return

        if not instance.driver:
            print("DEBUG: BŁĄD - Brak przypisanego KIEROWCY! Przekazanie nie zostanie utworzone.")
            return

        # 3. Sprawdzenie duplikatów
        if VehicleHandover.objects.filter(reservation=instance).exists():
            print("DEBUG: Przekazanie dla tej rezerwacji już istnieje.")
            return

        # 4. Próba utworzenia
        try:
            # Pobieramy aktualny przebieg auta, żeby wpisać go jako startowy
            start_mileage = int(instance.assigned_vehicle.przebieg) if instance.assigned_vehicle else 0

            VehicleHandover.objects.create(
                kierowca=instance.driver,
                pojazd=instance.assigned_vehicle,
                reservation=instance,
                data_wydania=instance.date_from,
                data_zwrotu=instance.date_to,
                przebieg_start=start_mileage,  # <-- Dodano automatyczny przebieg
                uwagi=f"Automatycznie z rezerwacji (ID: {instance.id})."
            )
            print(f"DEBUG: SUKCES! Utworzono przekazanie.")
        except Exception as e:
            print(f"DEBUG: WYJĄTEK przy tworzeniu przekazania: {e}")

    def perform_create(self, serializer):
        instance = serializer.save()
        self._create_handover_if_approved(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._create_handover_if_approved(instance)

# --- BRAKUJĄCA KLASA (DODANA) ---
class VehicleDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleDocumentDto

    def get_queryset(self):
        queryset = VehicleDocument.objects.all().order_by('-uploaded_at')
        vehicle_id = self.request.query_params.get('vehicle')
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
        return queryset


class GlobalSettingsViewSet(viewsets.ModelViewSet):
    queryset = GlobalSettings.objects.all()
    serializer_class = GlobalSettingsDto

    def get_object(self):
        obj, created = GlobalSettings.objects.get_or_create(pk=1)
        return obj

    def list(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return Response(serializer.data)


# AUTH
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    pin_2fa = request.data.get('pin_2fa')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        if user.rola == 'ADMIN' or user.is_staff:
            if pin_2fa != "1234": return Response({'detail': 'Wymagany PIN 2FA.'}, status=401)
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh), 'access': str(refresh.access_token),
            'user_role': user.rola, 'username': user.username,
            'first_name': user.first_name, 'last_name': user.last_name
        })
    return Response({'detail': 'Błędne dane.'}, status=401)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    company_name = request.data.get('company_name', '').strip()
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    if not username or not password: return Response({'detail': 'Wymagane dane.'}, status=400)
    if CustomUser.objects.filter(username=username).exists(): return Response({'detail': 'Użytkownik istnieje.'},
                                                                              status=400)
    user = CustomUser.objects.create_user(username=username, password=password, email=email, rola='DRIVER',
                                          first_name=first_name, last_name=last_name)
    company_obj, _ = FleetCompany.objects.get_or_create(nazwa=company_name, defaults={'nip': ''})
    Driver.objects.create(user=user, company=company_obj, aktywny=True)
    return Response({'detail': 'Konto utworzone.'}, status=201)


def mobile_app_view(request):
    return render(request, 'mobile.html')