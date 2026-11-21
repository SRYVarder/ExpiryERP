from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/read/', views.mark_as_read, name='mark_as_read'),
    path('notifications/mark-all-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('notifications/delete-read/', views.delete_read_notifications, name='delete_read_notifications'),
    path('notifications/<int:pk>/delete/', views.delete_notification, name='delete_notification'),
    path('notifications/unread-count/', views.unread_count, name='unread_count'),  # for HTMX badge
]