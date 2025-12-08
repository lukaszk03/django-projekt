# Master/Server/fleet_core/urls.py

# Zmień import widoków
from .views import VehicleViewSet, DriverViewSet, ServiceEventViewSet, DamageEventViewSet, login_view
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'drivers', DriverViewSet, basename='driver')
router.register(r'service_events', ServiceEventViewSet, basename='service_event')
router.register(r'damage_events', DamageEventViewSet, basename='damage_event') # NOWA TRASA

urlpatterns = [
    path('login/', login_view, name='login'),
    *router.urls
]