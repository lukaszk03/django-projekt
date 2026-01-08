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
from .models import Vehicle, Driver, DamageEvent, InsurancePolicy, CustomUser, VehicleHandover, ServiceEvent, Reservation, VehicleDocument, GlobalSettings, FleetCompany

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

        # 1. Przekazania (HANDOVER) - Ciemny Niebieski
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
                'color': '#0d47a1'  # <--- CIEMNY NIEBIESKI (Wydanie)
            })

            # Opis Zwrotu (Zostawiamy turkusowy/morski dla odróżnienia, lub też niebieski)
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
                    'color': '#17a2b8'  # Turkusowy (pozostawiamy dla czytelności zwrotu)
                })

        # 2. Szkody - Ciemniejszy Czerwony
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
                'color': '#8B0000'  # <--- CIEMNY CZERWONY (DarkRed)
            })

        # 3. Serwisy / Przeglądy / Naprawy (Kolory jak w Terminarzu)
        for s in vehicle.service_history.all():
            service_desc = s.opis
            if s.koszt and float(s.koszt) > 0:
                service_desc += f"\nKoszt: {s.koszt} PLN"

            # Logika kolorów zgodna z Terminarzem
            if s.typ_zdarzenia == 'PRZEGLAD':
                color = '#28a745'  # ZIELONY (Przegląd)
                icon = 'fa-check-double'
            elif s.typ_zdarzenia == 'NAPRAWA':
                color = '#dc3545'  # CZERWONY (Naprawa - jaśniejszy niż szkoda)
                icon = 'fa-tools'
            elif s.typ_zdarzenia == 'BADANIE_TECH':
                color = '#ffc107'  # ŻÓŁTY (Badanie Tech)
                icon = 'fa-clipboard-check'
            else:
                color = '#6c757d'  # Szary (Inne)
                icon = 'fa-wrench'

            events.append({
                'date': s.data_serwisu,
                'type': 'SERVICE',
                'title': f"{s.get_typ_zdarzenia_display()}",
                'description': service_desc,
                'icon': icon,
                'color': color
            })

        # 4. Polisy - Niebieski (jak w Terminarzu)
        for p in vehicle.policies.all():
            policy_desc = f"Ubezpieczyciel: {p.ubezpieczyciel}\nNr: {p.numer_polisy}"
            if p.koszt and float(p.koszt) > 0:
                policy_desc += f"\nKoszt: {p.koszt} PLN"

            # OC
            events.append({
                'date': p.data_waznosci_oc,
                'type': 'POLICY',
                'title': f"Koniec Polisy OC",
                'description': policy_desc,
                'icon': 'fa-file-contract',
                'color': '#007bff'  # <--- NIEBIESKI (Polisa, jak w kalendarzu)
            })

            # AC (jeśli jest)
            if p.data_waznosci_ac:
                events.append({
                    'date': p.data_waznosci_ac,
                    'type': 'POLICY',
                    'title': f"Koniec Polisy AC",
                    'description': policy_desc,
                    'icon': 'fa-shield-alt',
                    'color': '#007bff'  # <--- NIEBIESKI
                })

        # Sortowanie po dacie (od najnowszych)
        events.sort(key=lambda x: str(x['date']), reverse=True)

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

    # Funkcja pomocnicza: Sprawdza szkody i aktualizuje status auta
    def _update_vehicle_status(self, vehicle):
        # Sprawdzamy, czy ten pojazd ma jakiekolwiek OTWARTE szkody
        # (czyli status 'ZGLOSZONA' lub 'W_NAPRAWIE')
        ma_aktywne_szkody = DamageEvent.objects.filter(
            pojazd=vehicle,
            status_naprawy__in=['ZGLOSZONA', 'W_NAPRAWIE']
        ).exists()

        if ma_aktywne_szkody:
            vehicle.status = 'NIESPRAWNY'
        else:
            # Jeśli nie ma aktywnych szkód (wszystkie zamknięte lub brak szkód)
            vehicle.status = 'SPRAWNY'

        vehicle.save()

    # 1. Przy TWORZENIU nowej szkody
    def perform_create(self, serializer):
        damage = serializer.save()
        self._update_vehicle_status(damage.pojazd)

    # 2. Przy EDYCJI szkody (np. zmiana statusu na ZAMKNIETA)
    def perform_update(self, serializer):
        damage = serializer.save()
        self._update_vehicle_status(damage.pojazd)

    # 3. Przy USUWANIU szkody (np. usunięcie błędnego wpisu)
    def perform_destroy(self, instance):
        vehicle = instance.pojazd
        instance.delete()  # Najpierw usuwamy szkodę
        self._update_vehicle_status(vehicle)  # Potem przeliczamy status auta

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

    # 1. POPRAWKA: Pobieramy nazwę firmy z żądania
    company_name = request.data.get('company_name', '').strip()

    rola = 'DRIVER'
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')

    if not username or not password:
        return Response({'detail': 'Nazwa użytkownika i hasło są wymagane.'}, status=status.HTTP_400_BAD_REQUEST)

    # 2. POPRAWKA: Sprawdzamy, czy podano firmę
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

    # 3. POPRAWKA: Poprawna składnia (zamknięcie nawiasu)
    company_obj, created = FleetCompany.objects.get_or_create(
        nazwa=company_name,
        defaults={'nip': ''}
    )

    # 4. POPRAWKA: Tylko jedno tworzenie kierowcy
    Driver.objects.create(
        user=user,
        company=company_obj,
        numer_prawa_jazdy="",
        kategorie_prawa_jazdy="B"
    )

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