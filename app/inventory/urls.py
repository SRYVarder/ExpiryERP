from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'inventory'

router = DefaultRouter()
router.register(r'api/categories', views.CategoryViewSet, basename='api-category')
router.register(r'api/products', views.ProductViewSet, basename='api-product')
router.register(r'api/batches', views.BatchViewSet, basename='api-batch')
router.register(r'api/stock-movements', views.StockMovementViewSet, basename='api-stockmovement')

urlpatterns = [
    # Specific paths first (Reports must come before root redirect)
    path('reports/', include('reports.urls', namespace='reports')),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('expiring-soon/', views.expiring_soon_view, name='expiring_soon'),
    path('expired-batches/', views.expired_batches_view, name='expired_batches'),
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/bulk-upload/', views.bulk_product_upload, name='bulk_product_upload'),
    path('products/<str:icode>/', views.product_detail, name='product_detail'),
    path('products/<str:icode>/edit/', views.product_update, name='product_update'),
    path('products/<str:icode>/delete/', views.product_delete, name='product_delete'),

    # Category CRUD
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Batch CRUD
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/create/', views.batch_create, name='batch_create'),
    path('products/<str:product_icode>/batches/create/', views.batch_create, name='batch_create'),
    path('batches/<int:pk>/edit/', views.batch_update, name='batch_update'),
    path('batches/<int:pk>/delete/', views.batch_delete, name='batch_delete'),
    path('batches/bulk-upload/', views.bulk_batch_upload, name='bulk_batch_upload'),

    # Branch CRUD
    path("branches/", views.branch_list, name="branch_list"),
    path("branches/add/", views.branch_create, name="branch_create"),
    path("branches/<int:pk>/edit/", views.branch_update, name="branch_update"),
    path("branches/<int:pk>/delete/", views.branch_delete, name="branch_delete"),
    path("branch/switch/<int:pk>/", views.switch_branch, name="switch_branch"),

    # run expiry namually
    path('run-expiry-check/', views.run_expiry_check, name='run_expiry_check'),



    # Scanner
    path('scanner/', views.scanner, name='scanner'),

    # API
    path('api/', include(router.urls)),

    # Root redirect - MUST BE LAST
    #path('', views.root_redirect, name='home'),
]