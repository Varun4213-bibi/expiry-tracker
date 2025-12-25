from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from tracker import views

from django.http import FileResponse
from django.conf import settings
import os


# ✅ Service Worker view (ROOT SCOPE)
def service_worker(request):
    return FileResponse(
        open(os.path.join(settings.BASE_DIR, "expirytracker", "service-worker.js"), "rb"),
        content_type="application/javascript"
    )


urlpatterns = [
    path('admin/', admin.site.urls),

    path('login/', auth_views.LoginView.as_view(), name='login'),
    path(
        'logout/',
        auth_views.LogoutView.as_view(
            http_method_names=['get', 'post'],
            next_page='home',
            template_name='registration/logged_out.html'
        ),
        name='logout'
    ),
    path('signup/', views.signup, name='signup'),

    # ✅ REQUIRED FOR PUSH NOTIFICATIONS
    path('service-worker.js', service_worker),

    # App URLs
    path('', include('tracker.urls')),
]
