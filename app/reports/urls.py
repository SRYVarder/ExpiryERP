from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('expiry/', views.expiry_report, name='expiry_report'),
    path('stock-expiry/', views.stock_expiry_report, name='stock_expiry_report'),
]