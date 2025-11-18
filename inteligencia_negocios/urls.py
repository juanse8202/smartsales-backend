from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GenerateReportView, StandardReportView

urlpatterns = [
    path('reports/', GenerateReportView.as_view(), name='generate_report'),
    path('standard/<str:report_key>/', StandardReportView.as_view(), name='standard_report'),
]