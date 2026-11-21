from django.db import models
from django.core.validators import MinValueValidator
from simple_history.models import HistoricalRecords
from datetime import date 
from django.utils import timezone
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateWidget
# Create your models here.

class Branch(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True)  # e.g. WH1
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Branches"
        ordering = ["name"]

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    expiry_threshold_days = models.PositiveIntegerField(default=30)  # 1-90 as you asked

    def __str__(self):
        return self.name                    

    class Meta:
        verbose_name_plural = "Categories"



class Product(models.Model):
    name = models.CharField(max_length=255)
    icode = models.CharField(max_length=10, unique=True, editable=False, blank=True)
    scode = models.CharField(max_length=100, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    uom = models.CharField(max_length=20, choices=[
        ('pcs', 'Pieces'),
        ('kg', 'Kilograms'),
        ('l', 'Litres'),
        ('box', 'Boxes')
    ])
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    reorder_level = models.PositiveIntegerField(default=10)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="products", default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    extra_data = models.JSONField(default=dict, blank=True)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)  # first save → gets real database pk

        # Set icode from pk in 100001 series (only if empty)
        if is_new or not self.icode:
            desired_icode = str(100000 + self.pk)  # pk=1 → 100001
            if self.icode != desired_icode:
                self.icode = desired_icode
                # Save again only the icode field
                super().save(update_fields=['icode'])

    def __str__(self):
        return f"{self.icode} - {self.name}"

    class Meta:
        ordering = ['icode']

    @property
    def soh(self):
        return self.batches.filter(status='active').aggregate(
            total=models.Sum('current_quantity')
        )['total'] or 0



class Batch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100)
    manufacturing_date = models.DateField()
    
    # New Fields
    sell_by_date = models.DateField( null=True, blank=True, 
        help_text="Last day the product should be displayed at full price")
    salvage_date = models.DateField(null=True, blank=True, 
        help_text="Last day the product can be sold (possibly at discount)")
    expiry_date = models.DateField(help_text="Final hard expiry date - cannot be sold after this")

    current_quantity = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(0)])
    supplier_batch_ref = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('quarantined', 'Quarantined')
    ], default='active')

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="batches",
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if self.product_id and (self.branch_id is None):
            self.branch_id = self.product.branch_id
        super().save(*args, **kwargs)

    history = HistoricalRecords()

    class Meta:
        ordering = ['expiry_date']

    def is_near_expiry(self):
        if self.status != 'active':
            return False
        threshold = self.product.category.expiry_threshold_days if self.product.category else 30
        return (self.expiry_date - date.today()).days <= threshold

    
    def days_to_expiry(self):
          #"""Returns days until expiry. Negative = already expired"""
        if not self.expiry_date:
            return None
        delta = (self.expiry_date - date.today()).days
        return delta

    def is_expired(self):
        return self.days_to_expiry() is not None and self.days_to_expiry() < 0

    def expiry_status_display(self):
        """Nice human-readable text"""
        days = self.days_to_expiry()
        if days is None:
            return "No expiry date"
        if days < 0:
            return f"Expired {abs(days)} days ago"
        elif days == 0:
            return "Expires today"
        elif days == 1:
            return "Expires tomorrow"
        else:
            return f"{days} days left"

    def get_expiry_color(self):
        """For styling: green, amber, red"""
        days = self.days_to_expiry()
        if days is None:
            return "text-slate-400"
        if days < 0:
            return "text-red-400"
        elif days <= 7:
            return "text-amber-400"
        elif days <= 30:
            return "text-green-400"
        else:
            return "text-emerald-400"



    def __str__(self):
        return f"{self.batch_number} - {self.product.name}"

class BatchResource(resources.ModelResource):
    product = fields.Field(
        column_name='product_icode',
        attribute='product',
        widget=ForeignKeyWidget(Product, 'icode')
    )
    
    manufacturing_date = fields.Field(
        attribute='manufacturing_date',
        widget=DateWidget(format='%Y-%m-%d')
    )
    #sell_by_date = fields.Field(
    #    attribute='sell_by_date',
      #  widget=DateWidget(format='%Y-%m-%d')
   # )
   # salvage_date = fields.Field(
   #     attribute='salvage_date',
   #     widget=DateWidget(format='%Y-%m-%d')
   # )
    expiry_date = fields.Field(
        attribute='expiry_date',
        widget=DateWidget(format='%Y-%m-%d')
    )

    class Meta:
        model = Batch
        fields = (
            'product_icode', 'batch_number', 'manufacturing_date',
            'sell_by_date', 'salvage_date', 'expiry_date',
            'current_quantity', 'supplier_batch_ref'
        )
        export_order = fields
        import_id_fields = ['batch_number']

class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    movement_type = models.CharField(max_length=20, choices=[('receipt','Receipt'),('issue','Issue/Sale'),('adjustment','Adjustment')])
    quantity = models.DecimalField(max_digits=12, decimal_places=0)
    performed_by = models.ForeignKey('core.CustomUser', on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.movement_type} - {self.product.icode} | Qty: {self.quantity}"


