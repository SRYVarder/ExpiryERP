from datetime import date, timedelta
from django import forms
from .models import Product, Batch, Category, Branch
from import_export.formats.base_formats import XLSX


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'scode', 'category', 'uom',
                  'selling_price', 'cost_price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'bg-slate-700 text-white border border-slate-600 rounded-xl px-4 py-3 w-full focus:ring-2 focus:ring-teal-500 outline-none'}),
            'scode': forms.TextInput(attrs={'class': 'bg-slate-700 text-white border border-slate-600 rounded-xl px-4 py-3 w-full focus:ring-2 focus:ring-teal-500 outline-none'}),
            'selling_price': forms.NumberInput(attrs={'class': 'bg-slate-700 text-white border border-slate-600 rounded-xl px-4 py-3 w-full focus:ring-2 focus:ring-teal-500 outline-none'}),
            'cost_price': forms.NumberInput(attrs={'class': 'bg-slate-700 text-white border border-slate-600 rounded-xl px-4 py-3 w-full focus:ring-2 focus:ring-teal-500 outline-none'}),
            # Add category, uom, and branch here too if you want them styled
            'category': forms.Select(attrs={'class': 'bg-slate-700 text-white border border-slate-600 rounded-xl px-4 py-3 w-full'}),
            'uom': forms.Select(attrs={'class': 'bg-slate-700 text-white border border-slate-600 rounded-xl px-4 py-3 w-full'}),
            
        }

class BulkProductUploadForm(forms.Form):
    """Form for bulk Excel upload"""
    excel_file = forms.FileField(
        label="Upload Excel File",
        help_text="Upload an Excel file (.xlsx) with product data",
        widget=forms.FileInput(attrs={
            'class': 'bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full'
        })
    )       



class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = [
            'product', 'batch_number', 'manufacturing_date', 'sell_by_date', 
            'expiry_date', 'current_quantity', 'supplier_batch_ref'
        ]
        
        widgets = {
            # Use Django's built-in hidden widget instead of a hidden select field
            'product': forms.HiddenInput(attrs={'id': 'productHiddenInput'}),

            'batch_number': forms.TextInput(attrs={
                'class': 'bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full text-white'
            }),
            'manufacturing_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full focus:border-teal-500 text-white'
            }),
            
            'sell_by_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full focus:border-teal-500 text-white'
            }),
            'expiry_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full focus:border-teal-500 text-white'
            }),
            'current_quantity': forms.NumberInput(attrs={
                'class': 'bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full text-white'
            }),
            'supplier_batch_ref': forms.TextInput(attrs={
                'class': 'bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full text-white'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.all().order_by('icode')
        
        today = date.today()
        if not self.instance.pk:
            self.fields['manufacturing_date'].initial = today
            self.fields['expiry_date'].initial = today + timedelta(days=365)
            self.fields['sell_by_date'].initial = today + timedelta(days=300)
            

        self.fields['sell_by_date'].label = "Sell-By Date"
        self.fields['expiry_date'].label = "Expiry Date (Cannot sell after)"
        self.fields['manufacturing_date'].label = "Manufacturing Date"

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ['sell_by_date']:
            value = cleaned_data.get(field_name)
            if value == '' or value is None:
                cleaned_data[field_name] = None
        return cleaned_data



class BulkBatchUploadForm(forms.Form):
    file = forms.FileField(
        label="Upload Excel File",
        help_text="Excel file with columns: product_icode, batch_number, manufacturing_date, sell_by_date, salvage_date, expiry_date, current_quantity, supplier_batch_ref"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({
            'class': 'bg-slate-700 text-white border border-slate-600 rounded-xl px-4 py-3 w-full'
        })

    
    

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'expiry_threshold_days']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full focus:border-teal-500'}),
            'expiry_threshold_days': forms.NumberInput(attrs={'class': 'bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full'}),
        }

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ["name", "code", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full text-white"
            }),
            "code": forms.TextInput(attrs={
                "class": "bg-slate-700 border border-slate-600 rounded-xl px-4 py-3 w-full text-white"
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "rounded"}),
        }

