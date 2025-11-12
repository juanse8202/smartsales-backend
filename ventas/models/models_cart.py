"""
Modelos para el carrito de compras
"""
import uuid
from django.db import models
from django.conf import settings
from catalogo.models import Catalogo  # Importa tu modelo Catalogo


class Cart(models.Model):
    """
    Modelo para el carrito de compras
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        return sum([item.subtotal for item in self.items.all()])

    def __str__(self):
        return f"Carrito de {self.user.username if self.user else 'Anónimo'}"

    class Meta:
        db_table = 'ventas_cart'
        verbose_name = 'Carrito'
        verbose_name_plural = 'Carritos'


class CartItem(models.Model):
    """
    Modelo para los items del carrito
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    # AQUÍ EL CAMBIO CLAVE: Vinculamos con Catálogo, no con Producto específico
    catalogo = models.ForeignKey(Catalogo, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = [['cart', 'catalogo']]
        db_table = 'ventas_cart_item'
        verbose_name = 'Item del Carrito'
        verbose_name_plural = 'Items del Carrito'

    @property
    def subtotal(self):
        # Usamos el precio del catálogo
        return self.catalogo.precio * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.catalogo.nombre} en carrito"
