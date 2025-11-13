# ventas/management/commands/generate_fake_sales.py
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from ventas.models.models_venta import Venta
from administracion.models import Cliente

class Command(BaseCommand):
    help = 'Genera ventas falsas para entrenar el modelo de IA'

    def handle(self, *args, **options):
        self.stdout.write("Generando datos de ventas sintéticos...")
        
        # 1. Asegúrate de tener al menos un cliente
        cliente, created = Cliente.objects.get_or_create(
            nombre="Cliente de Prueba (Sintético)",
            defaults={'nit_ci': '1234567'}
        )
        if created:
            self.stdout.write(f"Cliente de prueba '{cliente.nombre}' creado.")

        # 2. Generar 100 ventas en los últimos 12 meses
        today = timezone.now()
        ventas_creadas = 0
        for _ in range(100):
            # Fecha aleatoria en los últimos 12 meses
            dias_atras = random.randint(1, 365)
            fecha_venta = today - relativedelta(days=dias_atras)
            
            # Valores aleatorios
            subtotal = Decimal(random.uniform(100.0, 5000.0))
            descuento = Decimal(random.uniform(0.0, 100.0))
            
            try:
                venta = Venta(
                    cliente=cliente,
                    fecha=fecha_venta, # ¡Importante! Asignar la fecha histórica
                    subtotal=subtotal,
                    descuento=descuento,
                    # (El modelo Venta recalculará el total al guardar)
                    estado='completada' # ¡Importante! Solo entrenamos con completadas
                )
                
                # Asignamos la fecha manualmente de nuevo para 'auto_now_add'
                # (Es un truco para datos históricos)
                venta.save()
                Venta.objects.filter(pk=venta.pk).update(fecha=fecha_venta)
                
                ventas_creadas += 1
            except Exception as e:
                self.stderr.write(f"Error creando venta: {e}")

        self.stdout.write(self.style.SUCCESS(f"¡Se crearon {ventas_creadas} ventas sintéticas!"))