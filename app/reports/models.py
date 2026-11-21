# reports/models.py
from django.db import models
from inventory.models import Product, Batch

class Report(models.Model):
    """Model to store generated reports (optional - for history)"""
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=[
        ('expiry', 'Expiry Report'),
        ('stock', 'Stock vs Expiry Report'),
        ('near_expiry', 'Near Expiry Report'),
    ])
    generated_by = models.ForeignKey('core.CustomUser', on_delete=models.SET_NULL, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    
    file_path = models.CharField(max_length=500, blank=True)  # for future file storage

    def __str__(self):
        return f"{self.title} - {self.generated_at.date()}"