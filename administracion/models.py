from django.db import models
from django.conf import settings
from django.utils import timezone
# Create your models here.

class RegistroBitacora(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='registros_bitacora')
    accion = models.CharField(max_length=50)
    descripcion = models.TextField()
    modulo = models.CharField(max_length=50, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        usuario_str = self.usuario.username if self.usuario else "Sistema"
        local_fecha_hora = timezone.localtime(self.fecha_hora)
        fecha_str = local_fecha_hora.strftime("%Y-%m-%d %H:%M:%S")
        return f'[{fecha_str}] {usuario_str} -> {self.accion} en {self.modulo or "N/A"}'
    
    class Meta:
        verbose_name = 'Registro de Bitácora'
        verbose_name_plural = 'Registros de Bitácora'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['-fecha_hora']),
        ]

class Departamento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['nombre']

class Ciudad(models.Model):
    nombre = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name='ciudades')

    class Meta:
        unique_together = ('nombre', 'departamento')
        verbose_name = 'Ciudad'
        verbose_name_plural = 'Ciudades'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.departamento.nombre})'

class Cliente(models.Model):
    CHOICE_RAZON_SOCIAL = {
        ('natural', 'Persona Natural'),
        ('juridica', 'Persona Jurídica'),
    }
    
    CHOICE_SEXO = {
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    }
    
    CHOICE_ESTADO = {
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    }
    
    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes')
    razon_social = models.CharField(max_length=20, choices=CHOICE_RAZON_SOCIAL, default='natural')
    sexo = models.CharField(max_length=1, choices=CHOICE_SEXO, null=True, blank=True)
    estado = models.CharField(max_length=10, choices=CHOICE_ESTADO, default='activo')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes_registrados')
    nit_ci = models.CharField(max_length=50, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-id']