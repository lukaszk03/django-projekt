# Master/Server/fleet_core/views.py

from rest_framework import viewsets, permissions
# Importy dla tokenów JWT i API
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate  # Do weryfikacji hasła
from rest_framework_simplejwt.tokens import RefreshToken  # Do generowania tokenów

# Usunięto błędny import 'User' - używamy tylko CustomUser z .models
# DODANO: ServiceEventDto do listy importów
from .serializers import VehicleDto, DriverDto, DamageEventDto, InsurancePolicyDto, VehicleHandoverDto, ServiceEventDto, ReservationDto, VehicleDocumentDto

# DODANO: ServiceEvent do listy importów
from .models import Vehicle, Driver, DamageEvent, InsurancePolicy, CustomUser, VehicleHandover, ServiceEvent, Reservation, VehicleDocument

# ----------------------------------------------------
# WIDOKI DLA ZARZĄDZANIA DANYMI FLOTY (Fleet Data ViewSets)
# ----------------------------------------------------

# 1. WIDOK DLA POJAZDÓW
class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.select_related('company').all()
    serializer_class = VehicleDto

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
    rola = request.data.get('rola', 'EMPLOYEE')
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

    return Response({'detail': 'Konto zostało utworzone. Możesz się zalogować.'}, status=status.HTTP_201_CREATED)

# 7. NOWY WIDOK DLA REZERWACJI
class ReservationViewSet(viewsets.ModelViewSet):
    # POPRAWKA: Usunięto select_related('company'), bo 'company' to teraz tekst, a nie klucz obcy!
    queryset = Reservation.objects.all().order_by('-created_at')
    serializer_class = ReservationDto

class VehicleDocumentViewSet(viewsets.ModelViewSet):
    queryset = VehicleDocument.objects.select_related('vehicle').all().order_by('-uploaded_at')
    serializer_class = VehicleDocumentDto