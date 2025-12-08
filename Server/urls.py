# Server/Server/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings # <-- DODAJ IMPORT!

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('fleet_core.urls')),
]

# Dodaj to na samym dole pliku
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns