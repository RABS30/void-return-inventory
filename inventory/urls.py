from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("input", views.input, name="input"),
    path("daftar", views.daftar, name="daftar"),
]


app_name = "inventory"