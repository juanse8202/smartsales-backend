"""
Importaciones centralizadas de vistas del módulo ventas
Para mantener compatibilidad con código existente
"""
from ventas.views.views_cart import CartViewSet
from ventas.views.views_venta import VentaViewSet, DetalleVentaViewSet, PagoViewSet

__all__ = [
    'CartViewSet',
    'VentaViewSet',
    'DetalleVentaViewSet',
    'PagoViewSet',
]
