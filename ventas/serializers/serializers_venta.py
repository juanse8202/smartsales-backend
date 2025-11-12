"""
Serializers para Ventas, Detalles de Venta y Pagos
"""
from rest_framework import serializers
from ventas.models import Venta, DetalleVenta, Pago
from administracion.serializers.serializers_cliente import ClienteSerializer
from catalogo.serializers.serializers_catalogo import CatalogoSerializer


# ==================== SERIALIZERS PARA DETALLE VENTA ====================

class DetalleVentaSerializer(serializers.ModelSerializer):
    """
    Serializer completo para DetalleVenta con información del producto
    """
    catalogo = CatalogoSerializer(read_only=True)
    catalogo_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = DetalleVenta
        fields = [
            'id',
            'venta',
            'catalogo',
            'catalogo_id',
            'cantidad',
            'precio_unitario',
            'subtotal',
            'descuento',
            'total',
        ]
        read_only_fields = ['id', 'subtotal', 'total']


class DetalleVentaCreateSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para crear detalles de venta
    """
    class Meta:
        model = DetalleVenta
        fields = [
            'catalogo_id',
            'cantidad',
            'precio_unitario',
            'descuento',
        ]
    
    def validate_cantidad(self, value):
        if value < 1:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value
    
    def validate_precio_unitario(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio unitario no puede ser negativo")
        return value


# ==================== SERIALIZERS PARA VENTA ====================

class VentaSerializer(serializers.ModelSerializer):
    """
    Serializer completo para Venta con detalles anidados
    """
    cliente = ClienteSerializer(read_only=True)
    detalles = DetalleVentaSerializer(many=True, read_only=True)
    total_productos = serializers.SerializerMethodField()
    
    class Meta:
        model = Venta
        fields = [
            'id',
            'cliente',
            'fecha',
            'subtotal',
            'impuesto',
            'descuento',
            'total',
            'estado',
            'costo_envio',
            'direccion',
            'detalles',
            'total_productos',
        ]
        read_only_fields = ['id', 'fecha', 'total']
    
    def get_total_productos(self, obj):
        """
        Retorna la cantidad total de productos en la venta
        """
        return sum(detalle.cantidad for detalle in obj.detalles.all())


class VentaListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar ventas
    """
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    total_productos = serializers.SerializerMethodField()
    
    class Meta:
        model = Venta
        fields = [
            'id',
            'cliente_nombre',
            'fecha',
            'total',
            'estado',
            'total_productos',
        ]
    
    def get_total_productos(self, obj):
        return sum(detalle.cantidad for detalle in obj.detalles.all())


class VentaCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear ventas con detalles anidados
    """
    detalles = DetalleVentaCreateSerializer(many=True, write_only=True)
    cliente_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Venta
        fields = [
            'cliente_id',
            'subtotal',
            'impuesto',
            'descuento',
            'costo_envio',
            'direccion',
            'estado',
            'detalles',
        ]
    
    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError("Debe incluir al menos un producto en la venta")
        return value
    
    def create(self, validated_data):
        """
        Crea la venta y sus detalles en una transacción
        """
        from django.db import transaction
        from administracion.models import Cliente
        
        detalles_data = validated_data.pop('detalles')
        cliente_id = validated_data.pop('cliente_id')
        
        # Validar que el cliente existe
        try:
            cliente = Cliente.objects.get(id=cliente_id, estado=True)
        except Cliente.DoesNotExist:
            raise serializers.ValidationError("Cliente no encontrado o inactivo")
        
        with transaction.atomic():
            # Crear la venta
            venta = Venta.objects.create(cliente=cliente, **validated_data)
            
            # Crear los detalles
            for detalle_data in detalles_data:
                DetalleVenta.objects.create(venta=venta, **detalle_data)
            
            # Registrar en bitácora
            from administracion.core.utils import registrar_bitacora
            registrar_bitacora(
                usuario=self.context['request'].user if self.context['request'].user.is_authenticated else None,
                accion='CREAR',
                modulo='VENTAS',
                detalle=f'Venta #{venta.id} creada para cliente {cliente.nombre}'
            )
        
        return venta


# ==================== SERIALIZERS PARA PAGOS ====================

class PagoSerializer(serializers.ModelSerializer):
    """
    Serializer para Pagos
    """
    venta_id = serializers.IntegerField(source='venta.id', read_only=True)
    
    class Meta:
        model = Pago
        fields = [
            'id',
            'venta_id',
            'fecha_pago',
            'monto',
            'moneda',
            'estado',
            'proveedor',
            'transaccion_id',
        ]
        read_only_fields = ['id', 'fecha_pago']
    
    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a 0")
        return value


class PagoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear pagos
    """
    venta_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Pago
        fields = [
            'venta_id',
            'monto',
            'moneda',
            'estado',
            'proveedor',
            'transaccion_id',
        ]
    
    def create(self, validated_data):
        """
        Crea el pago y actualiza el estado de la venta si se paga completo
        """
        from django.db import transaction
        
        venta_id = validated_data.pop('venta_id')
        
        # Validar que la venta existe
        try:
            venta = Venta.objects.get(id=venta_id)
        except Venta.DoesNotExist:
            raise serializers.ValidationError("Venta no encontrada")
        
        with transaction.atomic():
            # Crear el pago
            pago = Pago.objects.create(venta=venta, **validated_data)
            
            # Si el pago está completado, actualizar estado de venta
            if pago.estado == 'completado':
                venta.estado = 'completada'
                venta.save()
            
            # Registrar en bitácora
            from administracion.core.utils import registrar_bitacora
            registrar_bitacora(
                usuario=self.context['request'].user if self.context['request'].user.is_authenticated else None,
                accion='CREAR',
                modulo='PAGOS',
                detalle=f'Pago #{pago.id} registrado para venta #{venta.id}'
            )
        
        return pago
