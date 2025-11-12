from django.db import models
from django.utils import timezone
from datetime import timedelta

# Create your models here.
class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Marca'
        verbose_name_plural = 'Marcas'
        ordering = ['nombre']

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

class Catalogo(models.Model):
    CHOICE_ESTADO = {
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    }
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(null=True, blank=True)
    imagen_url = models.URLField(null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    meses_garantia = models.PositiveIntegerField(default=12)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True, related_name='catalogos')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='catalogos')
    estado = models.CharField(max_length=15, choices=CHOICE_ESTADO, default='activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.nombre} ({self.sku})'
    
    @property
    def stock_disponible(self):
        return self.productos.filter(estado='disponible').count()

    class Meta:
        verbose_name = 'Catálogo de Producto'
        verbose_name_plural = 'Catálogos de Productos'
        ordering = ['nombre']

class Producto(models.Model):
    CHOICE_ESTADO = {
        ('disponible', 'Disponible'),
        ('reservado', 'Reservado'),  
        ('vendido', 'Vendido'),       
        ('en_reparacion', 'En Reparación'), 
        ('dado_de_baja', 'Dado de Baja'), 
    }
    numero_serie = models.CharField(max_length=100, unique=True, db_index=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=15, choices=CHOICE_ESTADO, default='disponible')
    fecha_ingreso = models.DateTimeField(auto_now_add=True) 
    catalogo = models.ForeignKey(Catalogo, on_delete=models.CASCADE, related_name='productos', db_column='Catalogo_id')
    fecha_venta = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'N/S: {self.numero_serie} - {self.catalogo.nombre}'
    
    @property
    def garantia_vigente(self):
        """
        Devuelve True si el producto está vendido y aún dentro del periodo de garantía.
        """
        if self.estado == 'vendido' and self.fecha_venta:
            # Obtenemos los meses de garantía desde el catálogo relacionado
            meses = self.catalogo.meses_garantia
            # Calculamos la fecha de expiración (aproximada, sumando días)
            fecha_expiracion = self.fecha_venta + timedelta(days=meses*30)
            
            return timezone.now() <= fecha_expiracion
        return False
    
    @property
    def fecha_fin_garantia(self):
        """
        Devuelve la fecha exacta en que termina la garantía.
        """
        if self.fecha_venta:
            return self.fecha_venta + timedelta(days=self.catalogo.meses_garantia*30)
        return None

    class Meta:
        verbose_name = 'Ítem de Producto (Serializado)'
        verbose_name_plural = 'Ítems de Productos (Serializados)'
        ordering = ['-fecha_ingreso']
