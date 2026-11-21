# core/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    
    ROLE_CHOICES = [
        ('superuser', 'Super User'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
    ]
    
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='staff'
    )
    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'superuser'
        elif not self.role:
            self.role = 'staff'
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

   # Permission Helpers
    def can_manage_users(self):
        return self.role == ['superuser', 'manager', 'staff']

    def can_manage_inventory(self):
        return self.role in ['superuser', 'manager']

    def can_view_reports(self):
        return self.role in ['superuser', 'manager', 'staff']

    def can_create_batches(self):
        return self.role in ['superuser', 'manager', 'staff']

    # Which branches this user may access
    branches = models.ManyToManyField(
        "inventory.Branch",
        blank=True,
        related_name="users",
    )

    # Optional: remember last branch
    last_branch = models.ForeignKey(
        "inventory.Branch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )