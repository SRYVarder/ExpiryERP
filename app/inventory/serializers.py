from rest_framework import serializers
from datetime import date
from drf_spectacular.utils import extend_schema_field
from .models import Product, Batch, Category, StockMovement, Branch


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'expiry_threshold_days']


class BatchSerializer(serializers.ModelSerializer):
    """Serializer for Batch with expiry calculations"""
    
    days_to_expiry = serializers.SerializerMethodField()
    is_near_expiry = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        fields = [
            'id', 'batch_number', 'manufacturing_date', 'expiry_date',
            'current_quantity', 'supplier_batch_ref', 'status',
            'days_to_expiry', 'is_near_expiry', 'is_expired', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'status']

    @extend_schema_field(serializers.IntegerField())
    def get_days_to_expiry(self, obj):
        """Returns number of days until expiry"""
        if obj.expiry_date:
            return (obj.expiry_date - date.today()).days
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_is_near_expiry(self, obj):
        """Returns True if batch is near expiry"""
        return obj.is_near_expiry() if hasattr(obj, 'is_near_expiry') else False

    @extend_schema_field(serializers.BooleanField())
    def get_is_expired(self, obj):
        """Returns True if batch is expired"""
        return obj.status == 'expired'


class ProductSerializer(serializers.ModelSerializer):
    """Full Product serializer with calculated fields"""
    
    category = CategorySerializer(read_only=True)
    batches = BatchSerializer(many=True, read_only=True)
    
    # Fixed: Explicit type hint for 'soh' property
    soh = serializers.ReadOnlyField(help_text="Current Stock on Hand (calculated from active batches)")
    
    total_batches = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'icode', 'name', 'scode', 'category', 'uom',
            'selling_price', 'cost_price', 'reorder_level',
            'soh', 'total_batches', 'batches', 'branch', 'extra_data'
        ]
        read_only_fields = ['id', 'icode', 'soh', 'total_batches']

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total_batches(self, obj):
        """Returns count of batches for this product"""
        return obj.batches.count()


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Used for creating and updating products"""
    class Meta:
        model = Product
        fields = [
            'name', 'scode', 'category', 'uom', 'selling_price',
            'cost_price', 'reorder_level', 'branch', 'extra_data'
        ]


class BatchCreateUpdateSerializer(serializers.ModelSerializer):
    """Used for creating and updating batches"""
    class Meta:
        model = Batch
        fields = [
            'product', 'batch_number', 'manufacturing_date',
            'expiry_date', 'current_quantity', 'supplier_batch_ref'
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    performed_by_username = serializers.CharField(source='performed_by.username', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'batch', 'movement_type', 'quantity',
            'performed_by_username', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'performed_by_username', 'created_at']


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'is_active']