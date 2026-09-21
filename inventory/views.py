from django.shortcuts import render

# Create your views here.
def dashboard(request):
    return render(request, 'dashboard.html')

def input(request):
    return render(request, 'input.html')

def daftar(request):
    return render(request, 'daftar.html')