from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from inventory.models import Batch
from core.models import CustomUser
from .models import Notification
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_expiry_alerts():
    """
    Daily Celery task to check for near-expiry and expired batches
    and create notifications for managers and superusers.
    """
    today = timezone.now().date()
    managers = CustomUser.objects.filter(role__in=['manager', 'superuser'])

    if not managers.exists():
        logger.warning("No managers or superusers found. No notifications created.")
        return "No managers found"

    near_count = 0
    expired_count = 0

    # ========== 1. NEAR EXPIRY ==========
    near_expiry_batches = Batch.objects.filter(
        status='active',
        expiry_date__gte=today,                     # include today
        expiry_date__lte=today + timedelta(days=90)
    ).select_related('product', 'product__category')

    for batch in near_expiry_batches:
        # Safe threshold
        threshold = 30  # default
        if batch.product.category and hasattr(batch.product.category, 'expiry_threshold_days'):
            threshold = batch.product.category.expiry_threshold_days or 30

        days_left = (batch.expiry_date - today).days

        if 0 <= days_left <= threshold:
            for manager in managers:
                obj, created = Notification.objects.get_or_create(
                    user=manager,
                    batch=batch,
                    notification_type='near_expiry',
                    defaults={
                        'title': f'Near Expiry: {batch.product.name}',
                        'message': (
                            f'Batch {batch.batch_number} will expire in {days_left} day{"s" if days_left != 1 else ""}. '
                            f'Current quantity: {batch.current_quantity} {batch.product.uom}'
                        )
                    }
                )
                if created:
                    near_count += 1

    # ========== 2. EXPIRED ==========
    expired_batches = Batch.objects.filter(
        status='active',
        expiry_date__lt=today
    ).select_related('product')

    for batch in expired_batches:
        # Update status
        batch.status = 'expired'
        batch.save(update_fields=['status'])

        for manager in managers:
            obj, created = Notification.objects.get_or_create(
                user=manager,
                batch=batch,
                notification_type='expired',
                defaults={
                    'title': f'Batch Expired: {batch.product.name}',
                    'message': (
                        f'Batch {batch.batch_number} expired on {batch.expiry_date}. '
                        f'Quantity was: {batch.current_quantity}. Please take action.'
                    )
                }
            )
            if created:
                expired_count += 1

    result = f"Created {near_count} near-expiry and {expired_count} expired notifications."
    logger.info(result)
    return result