"""
Modelos para gestión de Ventas, Detalles de Venta y Pagos
Basado en el diagrama de base de datos proporcionado
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from administracion.models import Cliente
from catalogo.models import Catalogo


class Venta(models.Model):
    """
    Modelo para registrar las ventas realizadas
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='ventas',
        verbose_name='Cliente'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Venta'
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Subtotal'
    )
    impuesto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name='Impuesto'
    )
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name='Descuento'
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Total'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado'
    )
    costo_envio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name='Costo de Envío'
    )
    direccion = models.TextField(
        verbose_name='Dirección de Entrega',
        default='Por definir'
    )
    
    class Meta:
        db_table = 'ventas_venta'
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Venta #{self.id} - {self.cliente.nombre} - Bs. {self.total}"
    
    def calcular_total(self):
        """
        Calcula el total de la venta: subtotal + impuesto + costo_envio - descuento
        """
        self.total = self.subtotal + self.impuesto + self.costo_envio - self.descuento
        return self.total
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para calcular el total automáticamente
        """
        self.calcular_total()
        super().save(*args, **kwargs)


class DetalleVenta(models.Model):
    """
    Modelo para los detalles/items de cada venta
    """
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Venta'
    )
    catalogo = models.ForeignKey(
        Catalogo,
        on_delete=models.PROTECT,
        related_name='detalles_venta',
        verbose_name='Producto'
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Cantidad'
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Precio Unitario'
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Subtotal'
    )
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        verbose_name='Descuento'
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Total'
    )
    
    class Meta:
        db_table = 'ventas_detalle_venta'
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'
    
    def __str__(self):
        return f"{self.catalogo.nombre} x {self.cantidad}"
    
    def calcular_totales(self):
        """
        Calcula el subtotal y total del detalle
        """
        self.subtotal = self.precio_unitario * self.cantidad
        self.total = self.subtotal - self.descuento
        return self.total
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para calcular totales automáticamente
        """
        self.calcular_totales()
        super().save(*args, **kwargs)


class Pago(models.Model):
    """
    Modelo para registrar los pagos de las ventas
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('fallido', 'Fallido'),
        ('reembolsado', 'Reembolsado'),
    ]
    
    MONEDA_CHOICES = [
        ('BOB', 'Bolivianos'),
        ('USD', 'Dólares'),
        ('EUR', 'Euros'),
    ]
    
    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name='pagos',
        verbose_name='Venta'
    )
    fecha_pago = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Pago'
    )
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Monto'
    )
    moneda = models.CharField(
        max_length=3,
        choices=MONEDA_CHOICES,
        default='BOB',
        verbose_name='Moneda'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name='Estado'
    )
    proveedor = models.CharField(
        max_length=100,
        verbose_name='Proveedor de Pago',
        help_text='Ej: Stripe, PayPal, Transferencia Bancaria, etc.'
    )
    transaccion_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='ID de Transacción',
        help_text='ID único proporcionado por el proveedor de pago'
    )
    
    class Meta:
        db_table = 'ventas_pago'
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago']
    
    def __str__(self):
        return f"Pago #{self.id} - Venta #{self.venta.id} - {self.moneda} {self.monto}"
