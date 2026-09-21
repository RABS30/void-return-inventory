from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from . import storage

# Create your views here.
def dashboard(request):
    return render(request, 'dashboard.html')

def input(request):
    return render(request, 'input.html')

def daftar(request):
    return render(request, 'daftar.html')

# Ready demo views
def dashboard_ready(request):
    return render(request, 'dashboard-ready.html')

def input_ready(request):
    return render(request, 'input-ready.html')

def daftar_ready(request):
    return render(request, 'daftar-ready.html')

# API Endpoints for demo
@require_http_methods(["GET"])
def api_transactions(request):
    """Get all transactions"""
    transactions = storage.load_transactions()
    return JsonResponse({'success': True, 'data': transactions})

@csrf_exempt
@require_http_methods(["POST"])
def api_transaction_create(request):
    """Create new transaction"""
    try:
        data = json.loads(request.body)
        
        # Add ID and timestamp
        data['id'] = storage.get_next_id()
        
        # Load existing transactions
        transactions = storage.load_transactions()
        transactions.append(data)
        
        # Save
        storage.save_transactions(transactions)
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["DELETE"])
def api_transaction_delete(request, transaction_id):
    """Delete transaction"""
    try:
        transactions = storage.load_transactions()
        transactions = [t for t in transactions if t['id'] != transaction_id]
        storage.save_transactions(transactions)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["GET"])
def api_barcode_lookup(request, barcode):
    """Lookup barcode (dummy data)"""
    # Dummy barcode data
    dummy_barang = {
        '8992388101010': {'nama': 'Indomie Goreng 85g', 'hjual': 3500},
        '8993675610019': {'nama': 'Aqua Botol 600ml', 'hjual': 4000},
        '8996001600016': {'nama': 'Teh Pucuk Harum 350ml', 'hjual': 3000},
        '8998866123456': {'nama': 'Chitato Sapi Panggang 68g', 'hjual': 8500},
        '8991001234567': {'nama': 'Mie Sedaap Goreng 85g', 'hjual': 3200},
        '8992761111111': {'nama': 'Ultra Milk Coklat 200ml', 'hjual': 5500},
    }
    
    if barcode in dummy_barang:
        return JsonResponse({'success': True, 'data': dummy_barang[barcode]})
    else:
        return JsonResponse({'success': False, 'error': 'Barcode tidak ditemukan'}, status=404)