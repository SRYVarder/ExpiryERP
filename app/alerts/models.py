from django.db import models
from django.utils import timezone
from core.models import CustomUser
from inventory.models import Batch   # Direct import (recommended)

class Notification(models.Model):
    """
    In-app notification system for managers and superusers.
    Primarily used for near-expiry alerts and expired stock notifications 
    displayed on the dashboard and notifications page.
    """
    
    NOTIFICATION_TYPES = [
        ('near_expiry', 'Near Expiry'),
        ('expired', 'Stock Expired'),
        ('low_stock', 'Low Stock Alert'),
        ('system', 'System Alert'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="The user (manager or superuser) who receives the notification"
    )

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='near_expiry',
        help_text="Type of notification"
    )

    title = models.CharField(
        max_length=200,
        help_text="Short title, e.g. 'Near Expiry Alert' or 'Batch Expired'"
    )

    message = models.TextField(
        help_text="Detailed message about the expiry event or alert"
    )

    # Link to the affected batch (for quick navigation and context)
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="The batch that triggered this notification (if applicable)"
    )

    is_read = models.BooleanField(
        default=False,
        help_text="Whether the user has marked this notification as read"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the notification was created"
    )

    class Meta:
        ordering = ['-created_at']          # Newest first
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=['user', 'is_read']),      # Fast unread count queries
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"{self.title} - {self.user.username} ({self.created_at.date()})"

    def mark_as_read(self):
        """Helper method to mark a single notification as read"""
        self.is_read = True
        self.save(update_fields=['is_read'])

    def mark_as_unread(self):
        """Helper method (useful for testing or admin actions)"""
        self.is_read = False
        self.save(update_fields=['is_read'])

    @property
    def is_expired_alert(self):
        """Check if this is an expired stock notification"""
        return self.notification_type == 'expired'

    @property
    def days_ago(self):
        """Human-friendly "X days ago" for templates"""
        delta = timezone.now() - self.created_at
        if delta.days == 0:
            return "Today"
        elif delta.days == 1:
            return "Yesterday"
        return f"{delta.days} days ago"