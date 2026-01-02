# Master/Server/fleet_core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# UWAGA: Usunąłem ServiceEventViewSet z listy importów, bo już nie istnieje
from .views import (
    VehicleViewSet,
    DriverViewSet,
    DamageEventViewSet,
    InsurancePolicyViewSet,
    VehicleHandoverViewSet,
    login_view,
    register_view,
    ServiceEventViewSet
)

router = DefaultRouter()

# Rejestracja widoków w routerze
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'drivers', DriverViewSet, basename='driver')
router.register(r'service_events', ServiceEventViewSet, basename='service_event')
router.register(r'damage_events', DamageEventViewSet, basename='damage_event')
router.register(r'handovers', VehicleHandoverViewSet, basename='handover')
router.register(r'policies', InsurancePolicyViewSet, basename='policy')

urlpatterns = [
    # Ścieżki do logowania i rejestracji
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),

    # Ścieżki API generowane przez router
    path('', include(router.urls)),
]