"""
supply_chain_ai URL Configuration.
Routes root requests to the interactive dashboard and API endpoints.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='root-dashboard'),
    path('dashboard/', TemplateView.as_view(template_name='index.html'), name='interactive-dashboard'),
    path('api/v1/', include('inventory_core.urls')),
]
