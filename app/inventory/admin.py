from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import Product, Batch, StockMovement, Category, Branch

# Register your models here.

class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        import_id_fields =  ['icode']
        use_bulk = True  # Fast for large imports

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ['icode', 'name', 'soh', 'selling_price', 'category']
    search_fields = ['icode', 'name', 'scode']
    list_filter = ['category']
    

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")

# Register the rest similarly (Batch, StockMovement, etc.)
admin.site.register(Batch)
admin.site.register(StockMovement)
admin.site.register(Category)

