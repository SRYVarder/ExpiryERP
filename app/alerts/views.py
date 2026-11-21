from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
from .models import Notification

@login_required
def notification_list(request):
    """Display all notifications for the current user"""
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related('batch', 'batch__product').order_by('-created_at')

    unread_count = notifications.filter(is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'title': 'Notifications'
    }
    return render(request, 'alerts/notification_list.html', context)


@login_required
def mark_as_read(request, pk):
    """Mark a single notification as read"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    
    messages.success(request, "Notification marked as read.")
    
    # Support HTMX (for future AJAX marking)
    if request.headers.get('HX-Request'):
        return render(request, 'alerts/partials/notification_item.html', {'notification': notification})
    
    return redirect('alerts:notification_list')


@login_required
def mark_all_as_read(request):
    """Mark all unread notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('alerts:notification_list')


@login_required
def unread_count(request):
    """Simple view to return unread count (useful for dashboard badge with HTMX)"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return render(request, 'alerts/partials/unread_badge.html', {'count': count})

@login_required
def delete_read_notifications(request):
    if request.method == 'POST':
        deleted_count, _ = Notification.objects.filter(
            user=request.user,
            is_read=True
        ).delete()
        
        messages.success(request, f"Successfully deleted {deleted_count} read notification(s).")
    
    return redirect('alerts:notification_list')  # or 'inventory:dashboard'

@login_required
def delete_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    
    if request.method == 'POST':
        notification.delete()
        messages.success(request, "Notification deleted.")
    
    return redirect('alerts:notification_list')