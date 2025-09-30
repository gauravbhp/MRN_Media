# MRN/urls.py
from django.contrib import admin
from django.urls import path
from App import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.mrn_form, name='mrn_form'),
]