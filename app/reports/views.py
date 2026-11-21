# reports/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from datetime import date, timedelta
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from inventory.models import Batch, Product
from django.core.paginator import Paginator
from inventory.utils import require_active_branch

@login_required
def reports_dashboard(request):
    today = date.today()
    branch = require_active_branch(request)
    batches = Batch.objects.filter(
        product__branch=branch,
        status="active",
    
    )
    
    context = {
        'total_products': Product.objects.count(),
        'total_batches': Batch.objects.count(),
        'expired_batches': Batch.objects.filter(status='expired').count(),
        'near_expiry': Batch.objects.filter(
            status='active',
            expiry_date__lte=today + timedelta(days=30)
        ).count(),
        'today': today,
    }
    return render(request, 'reports/reports_dashboard.html', context)


@login_required
def expiry_report(request):
    today = date.today()
    branch = require_active_branch(request)
    
    
    # Available time ranges
    time_ranges = {
        7: "1 Week",
        14: "2 Weeks",
        30: "1 Month",
        60: "2 Months",
        90: "3 Months",
        180: "6 Months",
    }
    
    # Selected days (default 30)
    selected_days = int(request.GET.get('days', 30))
    if selected_days not in time_ranges:
        selected_days = 30

    # Base queryset
    batches = Batch.objects.filter(
        product__branch=branch,
        status='active',
        expiry_date__gte=today,
        expiry_date__lte=today + timedelta(days=selected_days)
    ).select_related('product')

    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        batches = batches.filter(
            Q(batch_number__icontains=search_query) |
            Q(product__name__icontains=search_query) |
            Q(product__icode__icontains=search_query)
        )

    batches = batches.order_by('expiry_date')

    # Export to Excel (exports ALL filtered results, not just current page)
    if request.GET.get('export') == 'excel':
        return export_expiry_report_excel(batches, selected_days)

    # Pagination
    paginator = Paginator(batches, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'batches': page_obj,
        'page_obj': page_obj,
        'selected_days': selected_days,
        'time_ranges': time_ranges,
        'today': today,
        'search_query': search_query,
        'total_count': batches.count(),
        'title': f'Expiry Report - Next {time_ranges[selected_days]}'
    }
    return render(request, 'reports/expiry_report.html', context)


@login_required
def stock_expiry_report(request):
    today = date.today()
    branch = require_active_branch(request)
    batches = Batch.objects.filter(
        product__branch=branch,
        status="active",
    )
    
    products = Product.objects.all().order_by('icode')

    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(icode__icontains=search_query)
        )

    report_data = []
    for product in products:
        active_batches = product.batches.filter(status='active')
        total_soh = sum(b.current_quantity for b in active_batches)
        expiring_soon = active_batches.filter(
            expiry_date__lte=today + timedelta(days=30)
        ).count()
        
        report_data.append({
            'product': product,
            'soh': total_soh,
            'expiring_soon': expiring_soon,
        })

    # Export (all filtered results)
    if request.GET.get('export') == 'excel':
        return export_stock_expiry_report_excel(report_data)

    # Pagination
    paginator = Paginator(report_data, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'report_data': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'total_count': len(report_data),
        'today': today,
    }
    return render(request, 'reports/stock_expiry_report.html', context)

# ===================== EXPORT FUNCTIONS =====================

def export_expiry_report_excel(batches, days):
    wb = Workbook()
    ws = wb.active
    ws.title = f"Expiry Report {days} Days"

    # Headers
    headers = ['Product Icode', 'Product Name', 'Batch Number', 'Expiry Date', 'Quantity', 'Days Left']
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)

    # Data
    for row, batch in enumerate(batches, 2):
        ws.cell(row=row, column=1, value=batch.product.icode)
        ws.cell(row=row, column=2, value=batch.product.name)
        ws.cell(row=row, column=3, value=batch.batch_number)
        ws.cell(row=row, column=4, value=batch.expiry_date)
        ws.cell(row=row, column=5, value=float(batch.current_quantity))

        # Correct way to get days_to_expiry
        days_left = batch.days_to_expiry() if callable(getattr(batch, 'days_to_expiry', None)) else getattr(batch, 'days_to_expiry', '')
        ws.cell(row=row, column=6, value=days_left)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=expiry_report_{days}days.xlsx'
    wb.save(response)
    return response


def export_stock_expiry_report_excel(report_data):
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock vs Expiry Report"

    headers = ['Product Icode', 'Product Name', 'Current Stock (SoH)', 'Batches Expiring Soon (30 days)']
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)

    for row, item in enumerate(report_data, 2):
        ws.cell(row=row, column=1, value=item['product'].icode)
        ws.cell(row=row, column=2, value=item['product'].name)
        ws.cell(row=row, column=3, value=float(item['soh']))
        ws.cell(row=row, column=4, value=item['expiring_soon'])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=stock_expiry_report.xlsx'
    wb.save(response)
    return response