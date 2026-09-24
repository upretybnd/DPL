from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path

from reports import views as report_views

from .sitemaps import SITEMAPS


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /reports/dashboard/",
        "Disallow: /reports/projects/",
        "Disallow: /reports/notifications/",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt),
    path('', include('web.urls')),
    path('', include('branches.urls')),
    path('branch/', include('branches.legacy_urls')),
    path('accounts/', include('accounts.urls')),
    path('discussion/', include('forum.urls')),
    path('reports/', include('reports.urls')),
    path('portal/', report_views.portal, name='portal'),
    path('mis/', include('branches.manage_urls')),
]

# Serve static and uploaded media in development (the web server handles these in production)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
