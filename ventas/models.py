"""
Importaciones centralizadas de todos los modelos del módulo ventas
Para mantener compatibilidad con código existente
"""
from ventas.models.models_cart import Cart, CartItem
from ventas.models.models_venta import Venta, DetalleVenta, Pago

# Exportar todos los modelos
__all__ = [
    'Cart',
    'CartItem',
    'Venta',
    'DetalleVenta',
    'Pago',
]
