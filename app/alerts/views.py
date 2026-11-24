from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from inventory.utils import require_active_branch
from .models import Notification


def _active_branch_notifications(request):
    """Helper to scope all notifications to the current user and active branch."""
    branch = require_active_branch(request)
    return Notification.objects.filter(
        user=request.user,
        batch__product__branch=branch,
    ).select_related('batch', 'batch__product')


@login_required
def notification_list(request):
    """Display notifications for the current user in the active branch"""
    notifications = _active_branch_notifications(request).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'title': 'Notifications',
    }
    return render(request, 'alerts/notification_list.html', context)


@login_required
def mark_as_read(request, pk):
    """Mark a single notification in the active branch as read"""
    notification = get_object_or_404(_active_branch_notifications(request), pk=pk)
    notification.mark_as_read()

    messages.success(request, "Notification marked as read.")

    if request.headers.get('HX-Request'):
        return render(request, 'alerts/partials/notification_item.html', {'notification': notification})

    return redirect('alerts:notification_list')


@login_required
def mark_all_as_read(request):
    """Mark all unread notifications in the active branch as read"""
    _active_branch_notifications(request).filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications in this branch marked as read.")
    return redirect('alerts:notification_list')


@login_required
def unread_count(request):
    """Return unread count for the active branch (useful for dashboard badge with HTMX)"""
    count = _active_branch_notifications(request).filter(is_read=False).count()
    return render(request, 'alerts/partials/unread_badge.html', {'count': count})


@login_required
def delete_read_notifications(request):
    """Delete only read notifications within the active branch"""
    if request.method == 'POST':
        deleted_count, _ = _active_branch_notifications(request).filter(
            is_read=True
        ).delete()

        messages.success(request, f"Successfully deleted {deleted_count} read notification(s).")

    return redirect('alerts:notification_list')


@login_required
def delete_notification(request, pk):
    """Delete a single notification only if it has already been read"""
    notification = get_object_or_404(_active_branch_notifications(request), pk=pk)

    if request.method == 'POST':
        if not notification.is_read:
            messages.error(request, "You must mark this notification as read before deleting it.")
            return redirect('alerts:notification_list')

        notification.delete()
        messages.success(request, "Notification deleted.")

    return redirect('alerts:notification_list')
