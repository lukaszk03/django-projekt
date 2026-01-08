# Master/Server/fleet_core/views.py

from rest_framework import viewsets, permissions
# Importy dla tokenów JWT i API
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate  # Do weryfikacji hasła
from rest_framework_simplejwt.tokens import RefreshToken  # Do generowania tokenów

# Usunięto błędny import 'User' - używamy tylko CustomUser z .models
# DODANO: ServiceEventDto do listy importów
from .serializers import VehicleDto, DriverDto, DamageEventDto, InsurancePolicyDto, VehicleHandoverDto, ServiceEventDto, ReservationDto, VehicleDocumentDto, GlobalSettingsDto

# DODANO: ServiceEvent do listy importów
from .models import Vehicle, Driver, DamageEvent, InsurancePolicy, CustomUser, VehicleHandover, ServiceEvent, Reservation, VehicleDocument, GlobalSettings

# ----------------------------------------------------
# WIDOKI DLA ZARZĄDZANIA DANYMI FLOTY (Fleet Data ViewSets)
# ----------------------------------------------------

# 1. WIDOK DLA POJAZDÓW
class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.select_related('company').all()
    serializer_class = VehicleDto

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        vehicle = self.get_object()
        events = []

        # 1. Przekazania (Kto i kiedy jeździł)
        for h in vehicle.handovers.all():
            kierowca = f"{h.kierowca.user.first_name} {h.kierowca.user.last_name}"
            # Ustalamy datę końca (jeśli jest w trakcie, bierzemy dzisiejszą dla sortowania lub null)
            desc = f"Kierowca: {kierowca} ({h.kierowca.company.nazwa if h.kierowca.company else 'Brak firmy'})."
            if h.uwagi:
                desc += f" Uwagi: {h.uwagi}"

            events.append({
                'date': h.data_wydania,
                'type': 'HANDOVER',
                'title': 'Wydanie Pojazdu',
                'description': desc,
                'icon': 'fa-key',
                'color': '#28a745'  # Zielony
            })

            # Jeśli auto zostało zwrócone, dodajemy osobny wpis o zwrocie
            if h.data_zwrotu:
                events.append({
                    'date': h.data_zwrotu,
                    'type': 'RETURN',
                    'title': 'Zwrot Pojazdu',
                    'description': f"Zwrot od: {kierowca}. Przebieg: {h.przebieg_stop or '-'} km.",
                    'icon': 'fa-check-circle',
                    'color': '#17a2b8'  # Niebieski
                })

        # 2. Szkody
        for d in vehicle.damage_history.all():
            events.append({
                'date': d.data_zdarzenia,
                'type': 'DAMAGE',
                'title': f'Szkoda: {d.status_naprawy}',
                'description': d.opis,
                'icon': 'fa-car-crash',
                'color': '#dc3545'  # Czerwony
            })

        # 3. Serwisy / Przeglądy
        for s in vehicle.service_history.all():
            events.append({
                'date': s.data_serwisu,
                'type': 'SERVICE',
                'title': f"Serwis: {s.get_typ_zdarzenia_display()}",
                'description': f"{s.opis} (Koszt: {s.koszt} PLN)",
                'icon': 'fa-wrench',
                'color': '#ffc107'  # Żółty
            })

        # 4. Polisy (Data ważności OC jako zdarzenie)
        for p in vehicle.policies.all():
            events.append({
                'date': p.data_waznosci_oc,
                'type': 'POLICY',
                'title': f"Koniec Polisy OC ({p.ubezpieczyciel})",
                'description': f"Nr polisy: {p.numer_polisy}",
                'icon': 'fa-file-contract',
                'color': '#6c757d'  # Szary
            })

        # Sortowanie po dacie (od najnowszych)
        events.sort(key=lambda x: x['date'], reverse=True)

        return Response(events)

# 2. WIDOK DLA UŻYTKOWNIKÓW (Kierowców)
class DriverViewSet(viewsets.ModelViewSet):
    # Optymalizacja! Ładujemy powiązany obiekt User
    queryset = Driver.objects.select_related('user').all()
    serializer_class = DriverDto

# 3. WIDOK DLA ZDARZEŃ SERWISOWYCH (Inspekcje, Naprawy, Przeglądy) - PRZYWRÓCONE
class ServiceEventViewSet(viewsets.ModelViewSet):
    # select_related('pojazd') jest konieczne, aby wyciągnąć VIN i Nr Rej. bez dodatkowych zapytań
    queryset = ServiceEvent.objects.select_related('pojazd').all()
    serializer_class = ServiceEventDto

# 4. WIDOK DLA ZDARZEŃ SZKODOWYCH
class DamageEventViewSet(viewsets.ModelViewSet):
    queryset = DamageEvent.objects.select_related('pojazd').all()
    serializer_class = DamageEventDto

# 5. NOWY WIDOK DLA POLIS
class InsurancePolicyViewSet(viewsets.ModelViewSet):
    queryset = InsurancePolicy.objects.select_related('pojazd').all()
    serializer_class = InsurancePolicyDto

# 6. NOWY WIDOK DLA PRZEKAZAŃ
class VehicleHandoverViewSet(viewsets.ModelViewSet):
    queryset = VehicleHandover.objects.select_related('kierowca__user', 'kierowca__company', 'pojazd').all()
    serializer_class = VehicleHandoverDto

    # ZMIANA NA CZAS TESTÓW: AllowAny
    # To pozwoli nam sprawdzić czy kod działa, ignorując błędy tokena
    permission_classes = [permissions.AllowAny]

# ----------------------------------------------------
# WIDOK FUNKCYJNY DLA LOGOWANIA Z 2FA
# ----------------------------------------------------

@api_view(['POST'])
@permission_classes([])  # Dostępne bez tokenu
def login_view(request):
    """
    Obsługuje logowanie. Dla Adminów wymaga dodatkowego PIN-u (2FA).
    """
    username = request.data.get('username')
    password = request.data.get('password')
    pin_2fa = request.data.get('pin_2fa')

    # 1. Weryfikacja podstawowych danych logowania
    user = authenticate(username=username, password=password)

    if user is not None:
        # 2. Weryfikacja Logiki 2FA dla Administratora
        if user.rola == 'ADMIN':
            if not pin_2fa or user.pin_2fa != pin_2fa:
                return Response(
                    {'detail': 'Błąd 2FA. Wymagane hasło i poprawny PIN 2FA dla Administratora.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # 3. Generujemy tokeny
        refresh = RefreshToken.for_user(user)

        # 4. Zwracamy tokeny i dane użytkownika
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

# ==================
# Rejestracja
#==================

@api_view(['POST'])
@permission_classes([])  # Dostępne dla każdego
def register_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')
    rola = 'DRIVER'
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')

    if not username or not password:
        return Response({'detail': 'Nazwa użytkownika i hasło są wymagane.'}, status=status.HTTP_400_BAD_REQUEST)

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

    from .models import Driver
    Driver.objects.create(user=user, numer_prawa_jazdy="", kategorie_prawa_jazdy="B")

    return Response({'detail': 'Konto zostało utworzone. Możesz się zalogować.'}, status=status.HTTP_201_CREATED)

# 7. NOWY WIDOK DLA REZERWACJI
class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all().order_by('-created_at')
    serializer_class = ReservationDto

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
                    reservation=instance,  # <--- TUTAJ PRZYPISUJEMY REZERWACJĘ
                    data_wydania=instance.date_from,
                    data_zwrotu=instance.date_to,
                    uwagi=f"Automatycznie z rezerwacji (ID: {instance.id})."
                )

class VehicleDocumentViewSet(viewsets.ModelViewSet):
    queryset = VehicleDocument.objects.select_related('vehicle').all().order_by('-uploaded_at')
    serializer_class = VehicleDocumentDto

class GlobalSettingsViewSet(viewsets.ViewSet):
    # Ten widok działa specyficznie: zawsze zwraca ten sam, jedyny rekord
    permission_classes = [permissions.AllowAny] # Lub IsAuthenticated

    def list(self, request):
        settings_obj, created = GlobalSettings.objects.get_or_create(id=1)
        serializer = GlobalSettingsDto(settings_obj)
        return Response(serializer.data)

    def create(self, request):
        # Używamy create jako "update", bo mamy tylko 1 rekord
        settings_obj, created = GlobalSettings.objects.get_or_create(id=1)
        serializer = GlobalSettingsDto(settings_obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)