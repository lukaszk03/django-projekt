# Master/Server/fleet_core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    VehicleViewSet,
    DriverViewSet,
    DamageEventViewSet,
    InsurancePolicyViewSet,
    VehicleHandoverViewSet,
    ReservationViewSet,
    login_view,
    register_view,
    ServiceEventViewSet,
    VehicleDocumentViewSet,
    GlobalSettingsViewSet,
    mobile_app_view  # <--- DODANO IMPORT WIDOKU MOBILNEGO
)

router = DefaultRouter()

# Rejestracja widoków w routerze API
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'drivers', DriverViewSet, basename='driver')
router.register(r'service_events', ServiceEventViewSet, basename='service_event')
router.register(r'damage_events', DamageEventViewSet, basename='damage_event')
router.register(r'handovers', VehicleHandoverViewSet, basename='handover')
router.register(r'policies', InsurancePolicyViewSet, basename='policy')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'vehicle_documents', VehicleDocumentViewSet, basename='vehicle_document')
router.register(r'settings', GlobalSettingsViewSet, basename='settings')

urlpatterns = [
    # Ścieżki do logowania i rejestracji
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),

    # NOWA ŚCIEŻKA DLA APLIKACJI MOBILNEJ:
    path('mobile/', mobile_app_view, name='mobile-app'),

    # Ścieżki API generowane przez router (musi być na końcu, żeby nie przesłaniało innych)
    path('', include(router.urls)),
]