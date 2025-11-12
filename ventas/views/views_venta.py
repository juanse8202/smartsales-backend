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


# Importar también models para usar Q en las consultas
from django.db import models
