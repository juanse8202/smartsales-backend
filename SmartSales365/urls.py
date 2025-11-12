"""
URL configuration for SmartSales365 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('api/', include('administracion.urls')),
    path('api/', include('catalogo.urls')),
    path('api/', include('ventas.urls')),
    path('api/finanzas/', include('finanzas.urls')),  # Rutas de pagos con Stripe
    path('api/', include('inteligencia_negocios.urls')),  # Rutas de inteligencia de negocios
    path('admin/', admin.site.urls),  # Admin de Django en /admin/
]
