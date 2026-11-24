from celery import shared_task
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from inventory.models import Batch
from core.models import CustomUser
from .models import Notification
import logging

logger = logging.getLogger(__name__)


def _recipients_for_branch(branch):
    """Return superusers plus managers assigned to this specific branch."""
    return CustomUser.objects.filter(
        Q(role='superuser') | Q(is_superuser=True) | Q(role='manager', branches=branch)
    ).distinct()


@shared_task
def check_expiry_alerts(branch_id=None):
    """
    Check for near-expiry and expired batches and create notifications.
    - If `branch_id` is provided (e.g., manual dashboard run), scans only that branch.
    - If `branch_id` is None (daily Celery beat), scans all branches and notifies each branch's managers + superusers.
    """
    today = timezone.now().date()
    near_count = 0
    expired_count = 0

    branch_filter = {'product__branch_id': branch_id} if branch_id else {}
    recipients_cache = {}

    def get_recipients(branch):
        if branch.id not in recipients_cache:
            recipients_cache[branch.id] = list(_recipients_for_branch(branch))
        return recipients_cache[branch.id]

    # ========== 1. NEAR EXPIRY ==========
    near_expiry_batches = Batch.objects.filter(
        status='active',
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=90),
        **branch_filter,
    ).select_related('product', 'product__category', 'product__branch')

    for batch in near_expiry_batches:
        threshold = 30
        if batch.product.category and hasattr(batch.product.category, 'expiry_threshold_days'):
            threshold = batch.product.category.expiry_threshold_days or 30

        days_left = (batch.expiry_date - today).days

        if 0 <= days_left <= threshold:
            for manager in get_recipients(batch.product.branch):
                _, created = Notification.objects.get_or_create(
                    user=manager,
                    batch=batch,
                    notification_type='near_expiry',
                    defaults={
                        'title': f'Near Expiry: {batch.product.name}',
                        'message': (
                            f'Batch {batch.batch_number} will expire in {days_left} day{"s" if days_left != 1 else ""}. '
                            f'Current quantity: {batch.current_quantity} {batch.product.uom}'
                        ),
                    },
                )
                if created:
                    near_count += 1

    # ========== 2. EXPIRED ==========
    expired_batches = Batch.objects.filter(
        status='active',
        expiry_date__lt=today,
        **branch_filter,
    ).select_related('product', 'product__branch')

    for batch in expired_batches:
        batch.status = 'expired'
        batch.save(update_fields=['status'])

        for manager in get_recipients(batch.product.branch):
            _, created = Notification.objects.get_or_create(
                user=manager,
                batch=batch,
                notification_type='expired',
                defaults={
                    'title': f'Batch Expired: {batch.product.name}',
                    'message': (
                        f'Batch {batch.batch_number} expired on {batch.expiry_date}. '
                        f'Quantity was: {batch.current_quantity}. Please take action.'
                    ),
                },
            )
            if created:
                expired_count += 1

    scope_label = f" for branch #{branch_id}" if branch_id else ""
    result = f"Created {near_count} near-expiry and {expired_count} expired notifications{scope_label}."
    logger.info(result)
    return result
