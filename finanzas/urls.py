"""
URLs para el módulo de Finanzas - Stripe
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CreatePaymentIntentVenta,
    VerifyPaymentIntentVenta,
    ConfirmPaymentAutoVenta,
    ConfirmPaymentWithCardVenta,
    PagoStripeViewSet,
    MisPagosView
)

router = DefaultRouter()
router.register(r'pagos-stripe', PagoStripeViewSet, basename='pago-stripe')

urlpatterns = [
    # Endpoints de Stripe (deben ir ANTES del router)
    path('stripe/create-payment-intent/', CreatePaymentIntentVenta.as_view(), name='stripe-create-payment'),
    path('stripe/confirm-payment-auto/', ConfirmPaymentAutoVenta.as_view(), name='stripe-confirm-auto'),
    path('stripe/confirm-payment-with-card/', ConfirmPaymentWithCardVenta.as_view(), name='stripe-confirm-card'),
    path('stripe/verify-payment/', VerifyPaymentIntentVenta.as_view(), name='stripe-verify-payment'),
    path('stripe/confirm-payment/', VerifyPaymentIntentVenta.as_view(), name='stripe-confirm-payment'),  # Alias
    
    # Endpoint para obtener solo los pagos del usuario autenticado
    path('mis-pagos/', MisPagosView.as_view(), name='mis-pagos'),
    
    # Router de pagos (consulta)
    path('', include(router.urls)),
]
