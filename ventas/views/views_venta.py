"""
ViewSets para gestión de Ventas, Detalles de Venta y Pagos
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Count, Avg
from ventas.models import Venta, DetalleVenta, Pago
from ventas.serializers.serializers_venta import (
    VentaSerializer,
    VentaListSerializer,
    VentaCreateSerializer,
    DetalleVentaSerializer,
    PagoSerializer,
    PagoCreateSerializer
)
from administracion.core.utils import registrar_bitacora
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
import joblib
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

MODEL_FILE_PATH = 'sales_model.pkl'

class VentaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de Ventas
    """
    queryset = Venta.objects.all().select_related('cliente').prefetch_related('detalles')
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        """
        Retorna el serializer apropiado según la acción
        """
        if self.action == 'list':
            return VentaListSerializer
        elif self.action == 'create':
            return VentaCreateSerializer
        return VentaSerializer
    
    def get_queryset(self):
        """
        Filtra ventas por cliente y estado si se proporcionan en query params
        """
        queryset = super().get_queryset()
        
        # Filtrar por cliente
        cliente_id = self.request.query_params.get('cliente', None)
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        
        # Filtrar por estado
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Crea una nueva venta con sus detalles
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        venta = serializer.save()
        
        # Retornar la venta completa con detalles
        response_serializer = VentaSerializer(venta)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Actualiza una venta
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Registrar en bitácora
        registrar_bitacora(
            usuario=request.user if request.user.is_authenticated else None,
            accion='ACTUALIZAR',
            modulo='VENTAS',
            detalle=f'Venta #{instance.id} actualizada'
        )
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina una venta
        """
        instance = self.get_object()
        venta_id = instance.id
        
        # Registrar en bitácora antes de eliminar
        registrar_bitacora(
            usuario=request.user if request.user.is_authenticated else None,
            accion='ELIMINAR',
            modulo='VENTAS',
            detalle=f'Venta #{venta_id} eliminada'
        )
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        """
        Cambia el estado de una venta
        Ruta: POST /api/ventas/{id}/cambiar_estado/
        Body: { "estado": "completada" }
        """
        venta = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        if nuevo_estado not in dict(Venta.ESTADO_CHOICES):
            return Response(
                {'error': 'Estado inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        venta.estado = nuevo_estado
        venta.save()
        
        # Registrar en bitácora
        registrar_bitacora(
            usuario=request.user if request.user.is_authenticated else None,
            accion='ACTUALIZAR',
            modulo='VENTAS',
            detalle=f'Estado de venta #{venta.id} cambiado a {nuevo_estado}'
        )
        
        serializer = self.get_serializer(venta)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Retorna estadísticas de ventas
        Ruta: GET /api/ventas/estadisticas/
        """
        from decimal import Decimal
        
        stats = Venta.objects.aggregate(
            total_ventas=Count('id'),
            ventas_pendientes=Count('id', filter=models.Q(estado='pendiente')),
            ventas_completadas=Count('id', filter=models.Q(estado='completada')),
            ventas_canceladas=Count('id', filter=models.Q(estado='cancelada')),
            ingresos_totales=Sum('total'),
            ticket_promedio=Avg('total')
        )
        
        # Convertir None a 0
        for key, value in stats.items():
            if value is None:
                stats[key] = Decimal('0.00') if 'ingresos' in key or 'promedio' in key else 0
        
        return Response(stats)
    
    @action(detail=False, methods=['get'], url_path='dashboard-sales-over-time')
    def dashboard_sales_over_time(self, request):
        """
        Devuelve las ventas totales agrupadas por día, mes o año.
        Usa un query param: ?periodo=dia (default), ?periodo=mes, ?periodo=anio
        
        Ruta por Día:   GET /api/ventas/dashboard-sales-over-time/
        Ruta por Mes:  GET /api/ventas/dashboard-sales-over-time/?periodo=mes
        Ruta por Año:  GET /api/ventas/dashboard-sales-over-time/?periodo=anio
        """
        
        # 1. Leemos el parámetro 'periodo' de la URL. Por defecto es 'dia'.
        periodo = request.query_params.get('periodo', 'dia').lower()
        
        queryset = self.get_queryset().filter(estado='completada')
        
        # 2. Decidimos qué función de truncamiento usar
        if periodo == 'mes':
            sales_data = queryset \
                .annotate(periodo_agrupado=TruncMonth('fecha')) \
                .values('periodo_agrupado') \
                .annotate(total_ventas=Sum('total')) \
                .order_by('periodo_agrupado')
                
        elif periodo == 'anio':
            sales_data = queryset \
                .annotate(periodo_agrupado=TruncYear('fecha')) \
                .values('periodo_agrupado') \
                .annotate(total_ventas=Sum('total')) \
                .order_by('periodo_agrupado')
        
        else: # Por defecto, agrupamos por día
            sales_data = queryset \
                .annotate(periodo_agrupado=TruncDate('fecha')) \
                .values('periodo_agrupado') \
                .annotate(total_ventas=Sum('total')) \
                .order_by('periodo_agrupado')
        
        # 3. Renombramos la clave para que el frontend la entienda
        # (El resultado de .values() es [{'periodo_agrupado': '...', 'total_ventas': ...}])
        # Lo cambiamos a [{'fecha': '...', 'total_ventas': ...}]
        
        # Nota: Convertimos la fecha a string para un JSON limpio
        response_data = [
            {
                'fecha': item['periodo_agrupado'].strftime('%Y-%m-%d'), 
                'total_ventas': item['total_ventas']
            } 
            for item in sales_data
        ]
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'], url_path='dashboard-products')
    def dashboard_products_report(self, request):
        """
        Devuelve el Top 5 o Bottom 5 de productos.
        Usa un query param: ?order=asc (para bottom) o ?order=desc (para top).

        Ruta (Top 5): GET /api/ventas/dashboard-products/
        Ruta (Bottom 5): GET /api/ventas/dashboard-products/?order=asc
        """

        # 1. Revisa el query param 'order'.
        order = request.query_params.get('order', 'desc').lower()
        
        # 2. Define el campo por el cual ordenar
        if order == 'asc':
            order_by_field = 'monto_total_vendido' # Ascendente (Bottom 5)
        else:
            order_by_field = '-monto_total_vendido' # Descendente (Top 5)

        # 3. Construye la consulta
        products_data = DetalleVenta.objects.filter(venta__estado='completada') \
            .values('catalogo__nombre') \
            .annotate(monto_total_vendido=Sum('total')) \
            .order_by(order_by_field)[:5] # <-- ¡Usa el campo dinámico!
        
        return Response(products_data)

    @action(detail=False, methods=['get'], url_path='dashboard-clients')
    def dashboard_clients_report(self, request):
        """
        Devuelve el Top 5 o Bottom 5 de clientes (los que más o menos han gastado).
        Usa un query param '?order=asc' para Bottom 5.
        Por defecto (sin query param), devuelve el Top 5.
        
        Ruta Top 5: GET /api/ventas/dashboard-clients/
        Ruta Bottom 5: GET /api/ventas/dashboard-clients/?order=asc
        """
        
        # 1. Leemos el parámetro 'order' de la URL.
        # Si no se envía, usa 'desc' (descendente) como valor por defecto.
        order_direction = request.query_params.get('order', 'desc').lower()

        # 2. Decidimos el campo por el cual ordenar
        if order_direction == 'asc':
            # Orden Ascendente = Menos ventas (Bottom 5)
            order_by_field = 'monto_total'
        else:
            # Orden Descendente = Más ventas (Top 5)
            order_by_field = '-monto_total'

        # 3. El resto de la consulta es idéntica
        queryset = self.get_queryset().filter(estado='completada')
        
        top_clients = queryset \
            .values('cliente__nombre', 'cliente__nit_ci') \
            .annotate(
                cantidad_compras=Count('id'),
                monto_total=Sum('total')
            ) \
            .order_by(order_by_field)[:5] # <-- 4. Usamos el campo dinámico
        
        return Response(top_clients)


class DetalleVentaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para Detalles de Venta
    """
    queryset = DetalleVenta.objects.all().select_related('venta', 'catalogo')
    serializer_class = DetalleVentaSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """
        Filtra detalles por venta si se proporciona en query params
        """
        queryset = super().get_queryset()
        
        venta_id = self.request.query_params.get('venta', None)
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)
        
        return queryset


class PagoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de Pagos
    """
    queryset = Pago.objects.all().select_related('venta')
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        """
        Retorna el serializer apropiado según la acción
        """
        if self.action == 'create':
            return PagoCreateSerializer
        return PagoSerializer
    
    def get_queryset(self):
        """
        Filtra pagos por venta y estado si se proporcionan
        """
        queryset = super().get_queryset()
        
        # Filtrar por venta
        venta_id = self.request.query_params.get('venta', None)
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)
        
        # Filtrar por estado
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Registra un nuevo pago
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pago = serializer.save()
        
        # Retornar el pago completo
        response_serializer = PagoSerializer(pago)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """
        Actualiza un pago
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Registrar en bitácora
        registrar_bitacora(
            usuario=request.user if request.user.is_authenticated else None,
            accion='ACTUALIZAR',
            modulo='PAGOS',
            detalle=f'Pago #{instance.id} actualizado'
        )
        
        return Response(serializer.data)

class SalesPredictionView(APIView):
    """
    Carga el modelo de IA entrenado y devuelve las predicciones
    de ventas para los próximos 6 meses.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # 1. Cargar el modelo guardado
            model = joblib.load(MODEL_FILE_PATH)
        except FileNotFoundError:
            return Response(
                {'error': 'Modelo no encontrado. Por favor, entrene el modelo primero.'}, 
                status=503 # Service Unavailable
            )
        except Exception as e:
            return Response({'error': f'Error al cargar el modelo: {str(e)}'}, status=500)

        # 2. Generar "features" para los próximos 6 meses
        predictions = []
        today = datetime.now()
        
        for i in range(1, 7): # Predecir los próximos 6 meses
            future_date = today + relativedelta(months=i)
            year = future_date.year
            month_num = future_date.month
            
            # Crear el DataFrame para predecir (debe tener las mismas columnas que 'X' en el entrenamiento)
            features = pd.DataFrame([[year, month_num]], columns=['year', 'month_num'])
            
            # 3. Hacer la predicción
            predicted_sales = model.predict(features)[0]
            
            predictions.append({
                'label': f'{year}-{month_num:02d}', # Formato '2026-01'
                'predicted_sales': round(predicted_sales, 2)
            })

        # 4. Devolver el JSON listo para el gráfico
        # Ej: [{'label': '2025-12', 'predicted_sales': 15000.00}, 
        #      {'label': '2026-01', 'predicted_sales': 18000.00}]
        return Response(predictions)


# Importar también models para usar Q en las consultas
from django.db import models
