from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ventas.views import CartViewSet, VentaViewSet, DetalleVentaViewSet, PagoViewSet

router = DefaultRouter()
# Rutas para carrito
router.register(r'cart', CartViewSet, basename='cart')

# Rutas para ventas
router.register(r'ventas', VentaViewSet, basename='venta')
router.register(r'detalle-ventas', DetalleVentaViewSet, basename='detalle-venta')
router.register(r'pagos', PagoViewSet, basename='pago')

urlpatterns = [
    path('', include(router.urls)),
]