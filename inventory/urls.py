from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    # path("", views.dashboard, name="dashboard"),
    # path("input", views.input, name="input"),
    # path("daftar", views.daftar, name="daftar"),
    
    path("", views.dashboard_ready, name="dashboard"),
    path("input", views.input_ready, name="input"),
    path("daftar", views.daftar_ready, name="daftar"),
    # Ready demo pages
    # path("dashboard-ready", views.dashboard_ready, name="dashboard_ready"),
    # path("input-ready", views.input_ready, name="input_ready"),
    # path("daftar-ready", views.daftar_ready, name="daftar_ready"),
]