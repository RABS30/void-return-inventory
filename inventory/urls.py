from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    # Main pages (now using ready versions)
    path("", views.dashboard_ready, name="dashboard"),
    path("input", views.input_ready, name="input"),
    path("daftar", views.daftar_ready, name="daftar"),
    
    # API endpoints for demo
    path("api/transactions", views.api_transactions, name="api_transactions"),
    path("api/transaction/create", views.api_transaction_create, name="api_transaction_create"),
    path("api/transaction/delete/<int:transaction_id>", views.api_transaction_delete, name="api_transaction_delete"),
    path("api/barcode/<str:barcode>", views.api_barcode_lookup, name="api_barcode_lookup"),
]