from django.shortcuts import render

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