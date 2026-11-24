import openpyxl
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from datetime import date, timedelta
from .models import Category, Product, Batch, StockMovement, Branch
from django.core.exceptions import PermissionDenied
from core.models import CustomUser
from alerts.models import Notification
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from .serializers import ProductSerializer
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import ProductForm, BatchForm, CategoryForm, BulkProductUploadForm, BranchForm
from django.core.paginator import Paginator
from alerts.tasks import check_expiry_alerts
from import_export import resources
from .models import BatchResource
from .forms import BulkBatchUploadForm
from tablib import Dataset
# Create your views here.
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .utils import (
    get_user_branches,
    get_active_branch,
    require_active_branch,
    products_qs,
    batches_qs,
    get_main_branch,
)



def root_redirect(request):
    """Redirect root URL based on login status"""
    if request.user.is_authenticated:
        return redirect('inventory:dashboard')   # Logged in → Dashboard
    else:
        return redirect('login')                 # Not logged in → Login page

@login_required
def loading_screen(request):
    """Intermediate loading screen after login or after permission errors"""
    # You can pass context if needed
    context = {
        'message': 'Preparing your dashboard...',
        'redirect_url': 'inventory:dashboard'
    }
    return render(request, 'loading.html', context)

@login_required
def dashboard(request):
    today = date.today()
    branch = require_active_branch(request)

    total_products = Product.objects.filter(branch=branch).count()
    total_soh = (
        Product.objects.filter(branch=branch).aggregate(
            total=Sum(
                "batches__current_quantity",
                filter=Q(batches__status="active"),
            )
        )["total"]
        or 0
    )

    near_expiry_qs = Batch.objects.filter(
        product__branch=branch,
        status="active",
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=90),
    )
    near_expiry = near_expiry_qs.count()

    expired_qs = Batch.objects.filter(
        product__branch=branch
    ).filter(Q(status="expired") | Q(expiry_date__lt=today))
    expired = expired_qs.count()

    expiring_soon = near_expiry_qs.select_related("product").order_by("expiry_date")[:15]
    expired_batches = expired_qs.select_related("product").order_by("expiry_date")[:15]

    notifications = []
    if getattr(request.user, "role", None) in ("superuser", "manager") or request.user.is_superuser:
        notifications = Notification.objects.filter(
            user=request.user, is_read=False
        )[:10]
        # Optional stricter: only alerts for this branch's batches
        # notifications = notifications.filter(batch__product__branch=branch)

    context = {
        "total_products": total_products,
        "total_soh": round(float(total_soh), 2),
        "near_expiry": near_expiry,
        "expired": expired,
        "expiring_soon": expiring_soon,
        "expired_batches": expired_batches,
        "notifications": notifications,
        "unread_count": Notification.objects.filter(
            user=request.user, is_read=False
        ).count(),
        "today": today,
    }
    return render(request, "inventory/dashboard.html", context)

@login_required
def expiring_soon_view(request):
    """Full page: only batches that are still valid and near expiry"""
    today = date.today()

    expiring_soon = Batch.objects.filter(
        status='active',
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=90)
    ).select_related('product').order_by('expiry_date')

    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        expiring_soon = expiring_soon.filter(
            Q(batch_number__icontains=search_query) |
            Q(product__name__icontains=search_query) |
            Q(product__icode__icontains=search_query)
        )



    # Optional pagination
    paginator = Paginator(expiring_soon, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'expiring_soon': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'total_count': expiring_soon.count(),
    }
    return render(request, 'inventory/expirysoon.html', context)


@login_required
def expired_batches_view(request):
    """Full page: only already expired batches"""
    today = date.today()

    expired_batches = Batch.objects.filter(
        Q(status='expired') | Q(expiry_date__lt=today)
    ).select_related('product').order_by('expiry_date')

     # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        expired_batches = expired_batches.filter(
            Q(batch_number__icontains=search_query) |
            Q(product__name__icontains=search_query) |
            Q(product__icode__icontains=search_query)
        )



    # Optional pagination
    paginator = Paginator(expired_batches, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'expired_batches': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'total_count': expired_batches.count(),
    }
    return render(request, 'inventory/expiredbatch.html', context)

@login_required
def product_list(request):
    branch = require_active_branch(request)
    products = Product.objects.filter(branch=branch).select_related(
        "category", "branch"
    ).prefetch_related("batches")

    search_query = request.GET.get("search", "").strip()
    if search_query:
        products = products.filter(
            Q(icode__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(scode__icontains=search_query)
        )

    category_filter = request.GET.get("category")
    if category_filter:
        products = products.filter(category__name=category_filter)

    products = products.order_by("icode")
    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    categories = Category.objects.all().order_by("name")

    return render(request, "inventory/product_list.html", {
        "products": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "categories": categories,
        "category_filter": category_filter,
        "total_products": products.count(),
    })

@login_required
def scanner(request):
    context = {
        'title': 'Barcode Scanner',
    }

    return render(request, 'inventory/scanner.html')

# Optional: Quick view for single product with all its batches
@login_required
def product_detail(request, icode):
    product = get_object_or_404(Product, icode=icode)
    batches = product.batches.all().order_by('expiry_date')  # FEFO order
    
    context = {
        'product': product,
        'batches': batches,
    }
    return render(request, 'inventory/product_detail.html', context)

@extend_schema(
    summary="List all products with current stock",
    description="Returns products including SoH and batch information (useful for POS or mobile apps)",
    tags=["Products"]
)
@api_view(['GET'])
def api_product_list(request):
    products = Product.objects.select_related('category').prefetch_related('batches')
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

# product crud

@login_required
def product_create(request):
    branch = require_active_branch(request)
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.branch = branch
            product.save()
            messages.success(request, f"Product {product.icode} created.")
            return redirect("inventory:product_list")
    else:
        form = ProductForm()
    return render(request, "inventory/product_form.html", {
        "form": form, "title": "Add New Product"
    })


@login_required
def product_update(request, icode):
    product = get_object_or_404(Product, icode=icode, branch=require_active_branch(request))

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated successfully!")
            return redirect('inventory:product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Edit Product'})


@login_required
def product_delete(request, icode):
    product = get_object_or_404(Product, icode=icode, branch=require_active_branch(request))
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted successfully!")
        return redirect('inventory:product_list')
    
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})


# ===================== CATEGORY CRUD =====================
@login_required
def category_list(request):
    categories = Category.objects.all().order_by('name')

    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        categories = categories.filter(name__icontains=search_query)
 
    # Pagination
    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'total_categories': categories.count(),
    }
    return render(request, 'inventory/category_list.html', context)


@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created successfully!")
            return redirect('inventory:category_list')
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Add New Category'})


@login_required
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully!")
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Edit Category'})


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Category deleted successfully!")
        return redirect('inventory:category_list')
    return render(request, 'inventory/category_confirm_delete.html', {'object': category})


# ===================== BATCH CRUD =====================
@login_required
def batch_list(request, product_icode=None):
    branch = require_active_branch(request)
    product = None

    if product_icode:
        product = get_object_or_404(Product, icode=product_icode, branch=branch)
        batches = Batch.objects.filter(product=product).select_related("product")
    else:
        batches = Batch.objects.filter(product__branch=branch).select_related("product")

    search_query = request.GET.get("search", "").strip()
    if search_query:
        batches = batches.filter(
            Q(batch_number__icontains=search_query)
            | Q(product__name__icontains=search_query)
            | Q(product__icode__icontains=search_query)
        )

    batches = batches.order_by("expiry_date")
    paginator = Paginator(batches, 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(request, "inventory/batch_list.html", {
        "batches": page_obj,
        "page_obj": page_obj,
        "product": product,
        "search_query": search_query,
    })

@login_required
def batch_create(request, product_icode=None):
    branch = require_active_branch(request)
    product = None
    if product_icode:
        product = get_object_or_404(Product, icode=product_icode, branch=branch)

    if request.method == "POST":
        form = BatchForm(request.POST)
        # Limit product choices to this branch
        form.fields["product"].queryset = Product.objects.filter(branch=branch).order_by("name")
        if form.is_valid():
            batch = form.save(commit=False)
            if batch.product.branch_id != branch.id:
                messages.error(request, "Product is not in the active branch.")
                return redirect("inventory:batch_create")
            batch.branch = branch
            batch.save()
            messages.success(request, f"Batch '{batch.batch_number}' created.")
            return redirect("inventory:product_detail", icode=batch.product.icode)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = BatchForm(initial={"product": product} if product else None)
        form.fields["product"].queryset = Product.objects.filter(branch=branch).order_by("name")
        form.fields["product"].label_from_instance = (
            lambda obj: f"{obj.name} ({obj.icode})"
        )

    return render(request, "inventory/batch_form.html", {
        "form": form,
        "title": "Create New Batch",
        "product": product,
    })

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

@login_required
def batch_update(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    product = batch.product

    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
    else:
        form = BatchForm(instance=batch)

    # 1. Lock product on edit so Django automatically keeps `batch.product`
    if 'product' in form.fields:
        form.fields['product'].disabled = True
        form.fields['product'].required = False

    # 2. Ensure existing dates render in ISO format (YYYY-MM-DD) for <input type="date">
    for field in form.fields.values():
        if isinstance(field, forms.DateField):
            field.widget.format = '%Y-%m-%d'
            if getattr(field.widget, 'input_type', None) != 'date':
                field.widget.input_type = 'date'

    if request.method == 'POST':
        if form.is_valid():
            updated_batch = form.save(commit=False)
            updated_batch.product = product  # Guaranteed to stay linked
            updated_batch.save()

            messages.success(request, f"Batch {updated_batch.batch_number} updated successfully!")
            return redirect('inventory:product_detail', icode=product.icode)
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, 'inventory/batch_form.html', {
        'form': form,
        'batch': batch,
        'product': product,
        'title': 'Edit Batch',
    })


@login_required
def batch_delete(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    product_icode = batch.product.icode
    if request.method == 'POST':
        batch.delete()
        messages.success(request, "Batch deleted successfully!")
        return redirect('inventory:product_detail', icode=product_icode)
    return render(request, 'inventory/batch_confirm_delete.html', {'batch': batch})

# ===================== BULK PRODUCT UPLOAD =====================
@login_required
def bulk_product_upload(request):
    if request.method == 'POST':
        form = BulkProductUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            
            try:
                wb = openpyxl.load_workbook(excel_file)
                sheet = wb.active
                
                success_count = 0
                error_count = 0
                
                # Skip header row (row 1)
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    try:
                        name, scode, category_name, uom, selling_price, cost_price, reorder_level = row[:7]
                        
                        # Get or create category
                        category = None
                        if category_name:
                            category, _ = Category.objects.get_or_create(name=category_name)
                        
                        # Get default branch
                        branch = Branch.objects.first()
                        
                        Product.objects.create(
                            name=name,
                            scode=scode or "",
                            category=category,
                            uom=uom or "pcs",
                            selling_price=selling_price or 0,
                            cost_price=cost_price or 0,
                            reorder_level=reorder_level or 10,
                            branch=branch
                        )
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        print(f"Error processing row: {e}")
                
                messages.success(request, f"Successfully imported {success_count} products. Errors: {error_count}")
                return redirect('inventory:product_list')
                
            except Exception as e:
                messages.error(request, f"Failed to process Excel file: {str(e)}")
    else:
        form = BulkProductUploadForm()
    
    return render(request, 'inventory/bulk_product_upload.html', {'form': form})

# ===================== BULK BATCH UPLOAD =====================


@login_required
def bulk_batch_upload(request):
    if request.method == 'POST':
        form = BulkBatchUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            
            # Determine the file extension (format)
            file_extension = file.name.split('.')[-1].lower()
            if file_extension not in ['csv', 'xlsx', 'xls']:
                messages.error(request, "Unsupported file format. Please upload CSV or Excel.")
                return render(request, 'inventory/bulk_batch_upload.html', {'form': form, 'title': 'Bulk Batch Upload'})

            # Initialize tablib dataset
            dataset = Dataset()
            try:
                # Read and load the data based on its format
                if file_extension == 'csv':
                    dataset.load(file.read().decode('utf-8'), format='csv')
                else:
                    dataset.load(file.read(), format=file_extension)
            except Exception as e:
                messages.error(request, f"Failed to parse file: {str(e)}")
                return render(request, 'inventory/bulk_batch_upload.html', {'form': form, 'title': 'Bulk Batch Upload'})


            # Initialize resource and run import
            resource = BatchResource()
            result = resource.import_data(dataset, dry_run=False)
            
            if result.has_errors():
                messages.error(request, "Some rows failed to import. Please check your file.")
                # Optional: You can inspect result.row_errors() here to debug
            else:
                messages.success(request, f"Successfully imported {len(dataset)} batches!")
                return redirect('inventory:batch_list')
    else:
        form = BulkBatchUploadForm()

    return render(request, 'inventory/bulk_batch_upload.html', {
        'form': form,
        'title': 'Bulk Batch Upload'
    })


# ===================== MANUAL EXPIRY CHECK =====================
@login_required
def run_expiry_check(request):
    """Manually trigger the expiry check task"""
    if request.method == 'POST':
        try:
            # Run the task immediately (no Celery needed)
            result = check_expiry_alerts()
            
            messages.success(
                request, 
                f"Expiry check completed! {result}"
            )
        except Exception as e:
            messages.error(request, f"Error running expiry check: {str(e)}")
        
        return redirect('inventory:dashboard')
    
    return redirect('inventory:dashboard')

# ===================== BRANCH CRUD  =====================

def _require_manager(request):
    if not (
        request.user.is_superuser
        or getattr(request.user, "role", None) in ("superuser", "manager")
    ):
        raise PermissionDenied


@login_required
def switch_branch(request, pk):
    allowed = get_user_branches(request.user)
    branch = get_object_or_404(allowed, pk=pk)
    request.session["active_branch_id"] = branch.id
    request.user.last_branch = branch
    request.user.save(update_fields=["last_branch"])
    messages.success(request, f"Switched to {branch.name}")
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect("inventory:dashboard")


@login_required
def branch_list(request):
    _require_manager(request)
    branches = Branch.objects.all().order_by("name")
    search_query = request.GET.get("search", "").strip()
    if search_query:
        branches = branches.filter(
            Q(name__icontains=search_query) | Q(code__icontains=search_query)
        )
    paginator = Paginator(branches, 15)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    return render(request, "inventory/branch_list.html", {
        "branches": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "total_count": branches.count(),
    })


@login_required
def branch_create(request):
    _require_manager(request)
    if request.method == "POST":
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Branch created.")
            return redirect("inventory:branch_list")
    else:
        form = BranchForm()
    return render(request, "inventory/branch_form.html", {
        "form": form, "title": "Add Branch"
    })


@login_required
def branch_update(request, pk):
    _require_manager(request)
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == "POST":
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, "Branch updated.")
            return redirect("inventory:branch_list")
    else:
        form = BranchForm(instance=branch)
    return render(request, "inventory/branch_form.html", {
        "form": form, "title": "Edit Branch"
    })


@login_required
def branch_delete(request, pk):
    _require_manager(request)
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == "POST":
        if branch.products.exists():
            messages.error(request, "Cannot delete a branch that still has products.")
            return redirect("inventory:branch_list")
        branch.delete()
        messages.success(request, "Branch deleted.")
        return redirect("inventory:branch_list")
    return render(request, "inventory/branch_confirm_delete.html", {"object": branch})



# ===================== DRF API VIEWS =====================


from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductCreateUpdateSerializer,
    BatchSerializer,
    BatchCreateUpdateSerializer,
    StockMovementSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Category CRUD - List, Create, Update, Delete", tags=["Categories"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category', 'branch').prefetch_related('batches')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        return ProductSerializer

    @extend_schema(summary="Product CRUD with SoH and Batches", tags=["Products"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.select_related('product')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return BatchSerializer
        return BatchCreateUpdateSerializer

    @extend_schema(summary="Batch CRUD with Expiry Calculations", tags=["Batches"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class StockMovementViewSet(viewsets.ModelViewSet):
    queryset = StockMovement.objects.select_related('product', 'batch', 'performed_by')
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
