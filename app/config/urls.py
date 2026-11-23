"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django import views
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.contrib.auth import views as auth_views
from inventory.views import loading_screen
from django.shortcuts import redirect
from django.contrib.auth.views import LoginView, LogoutView



urlpatterns = [
    path('admin/', admin.site.urls),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('alerts/', include('alerts.urls', namespace='alerts')),
    path('core/', include('core.urls', namespace='users')),

    # Authentication
   # Root URL → redirects to login if not logged in, or dashboard if logged in
    path('', lambda request: redirect('login' if not request.user.is_authenticated else 'inventory:dashboard'), name='root'),

    # Login & Logout at clean URLs
    path('login/', LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,   # Important: logged-in users go to dashboard
    ), name='login'),

    # Loading Screen
    path('loading/', loading_screen, name='loading'),

    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    


# ===== OpenAPI / Swagger Documentation =====
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),                    # Raw OpenAPI JSON
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),   # Swagger UI (most popular)
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),       # ReDoc (alternative nice UI)
]

handler403 = 'config.settings.handler403'