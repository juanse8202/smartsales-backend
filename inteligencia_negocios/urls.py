from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GenerateReportView

urlpatterns = [
    path('inteligencia_negocios/reportes/', GenerateReportView.as_view(), name='generate_report'),
]