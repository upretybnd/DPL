from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('web.urls')),
    path('branch/', include('branches.urls')),
    path('accounts/', include('accounts.urls')),
    path('discussion/', include('forum.urls')),
]

# Serve static files
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve media files (uploads)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
