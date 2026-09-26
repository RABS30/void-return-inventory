
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("inventory.urls", namespace="inventory")),
]

# Sajikan file media (foto upload) selama development (runserver, DEBUG=True).
# Di production, file media disajikan oleh Nginx (lihat AGENTS.md).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
