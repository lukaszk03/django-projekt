# Master/Server/fleet_core/views.py

from rest_framework import viewsets
# Importy dla tokenów JWT i API
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate  # Do weryfikacji hasła
from rest_framework_simplejwt.tokens import RefreshToken  # Do generowania tokenów

from .serializers import VehicleDto, DriverDto, ServiceEventDto, DamageEventDto, InsurancePolicyDto
from .models import Vehicle, Driver, ServiceEvent, DamageEvent, InsurancePolicy

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


# 3. WIDOK DLA ZDARZEŃ SERWISOWYCH
class ServiceEventViewSet(viewsets.ModelViewSet):
    # Optymalizacja! Ładujemy powiązany obiekt Vehicle
    queryset = ServiceEvent.objects.select_related('pojazd').all()
    serializer_class = ServiceEventDto

# 4. WIDOK DLA ZDARZEŃ SZKODOWYCH
class DamageEventViewSet(viewsets.ModelViewSet):
    # Możesz dodać uprawnienia IsAuthenticated, jeśli jeszcze nie masz ustawionych domyślnych
    # permission_classes = [permissions.IsAuthenticated]
    queryset = DamageEvent.objects.select_related('pojazd').all()
    serializer_class = DamageEventDto

# 5. NOWY WIDOK DLA POLIS
class InsurancePolicyViewSet(viewsets.ModelViewSet):
    queryset = InsurancePolicy.objects.select_related('pojazd').all()
    serializer_class = InsurancePolicyDto

# ----------------------------------------------------
# WIDOK FUNKCYJNY DLA LOGOWANIA Z 2FA (Authentication View)
# ----------------------------------------------------

@api_view(['POST'])
@permission_classes([])  # Oznacza, że ten widok jest dostępny bez tokenu (dla niezalogowanych)
def login_view(request):
    """
    Obsługuje logowanie. Dla Adminów wymaga dodatkowego PIN-u (2FA).
    """
    username = request.data.get('username')
    password = request.data.get('password')
    pin_2fa = request.data.get('pin_2fa')

    # 1. Weryfikacja podstawowych danych logowania (username i password)
    user = authenticate(username=username, password=password)

    if user is not None:

        # 2. Weryfikacja Logiki 2FA dla Administratora
        if user.rola == 'ADMIN':
            # Jeśli Admin nie podał PIN-u lub PIN jest nieprawidłowy
            if not pin_2fa or user.pin_2fa != pin_2fa:
                return Response(
                    {'detail': 'Błąd 2FA. Wymagane hasło i poprawny PIN 2FA dla Administratora.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # 3. Jeśli weryfikacja (w tym 2FA) przeszła pomyślnie, generujemy tokeny
        refresh = RefreshToken.for_user(user)

        # 4. Zwracamy tokeny i dane użytkownika
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user_role': user.rola,
            'username': user.username
        }, status=status.HTTP_200_OK)

    # W przypadku niepowodzenia uwierzytelniania
    return Response(
        {'detail': 'Nieprawidłowa nazwa użytkownika lub hasło.'},
        status=status.HTTP_401_UNAUTHORIZED
    )