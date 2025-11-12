"""
Serializers para gestión de pagos con Stripe
"""
from rest_framework import serializers
from ventas.models import Pago, Venta
from administracion.models import Cliente


class PagoStripeListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar pagos
    """
    cliente_nombre = serializers.CharField(source='venta.cliente.nombre', read_only=True)
    venta_id = serializers.IntegerField(source='venta.id', read_only=True)
    
    class Meta:
        model = Pago
        fields = [
            'id',
            'venta_id',
            'cliente_nombre',
            'monto',
            'moneda',
            'estado',
            'proveedor',
            'fecha_pago',
            'transaccion_id'
        ]


class PagoStripeSerializer(serializers.ModelSerializer):
    """
    Serializer completo para pagos con Stripe
    """
    venta_info = serializers.SerializerMethodField()
    cliente_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Pago
        fields = [
            'id',
            'venta',
            'venta_info',
            'cliente_info',
            'monto',
            'moneda',
            'estado',
            'proveedor',
            'transaccion_id',
            'fecha_pago'
        ]
        read_only_fields = ['id', 'fecha_pago', 'transaccion_id']
    
    def get_venta_info(self, obj):
        """Información de la venta asociada"""
        if obj.venta:
            return {
                'id': obj.venta.id,
                'total': float(obj.venta.total),
                'estado': obj.venta.estado,
                'fecha': obj.venta.fecha.strftime('%Y-%m-%d %H:%M:%S')
            }
        return None
    
    def get_cliente_info(self, obj):
        """Información del cliente"""
        if obj.venta and obj.venta.cliente:
            cliente = obj.venta.cliente
            return {
                'id': cliente.id,
                'nombre': cliente.nombre,
                'email': cliente.email if hasattr(cliente, 'email') else None
            }
        return None


class PagoStripeCreateSerializer(serializers.Serializer):
    """
    Serializer para crear un pago con Stripe
    """
    venta_id = serializers.IntegerField(required=True)
    monto = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text='Monto a pagar. Si no se especifica, se usa el total de la venta'
    )
    moneda = serializers.ChoiceField(
        choices=['BOB', 'USD', 'EUR'],
        default='BOB',
        required=False
    )
    descripcion = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Descripción del pago'
    )
    
    def validate_venta_id(self, value):
        """Validar que la venta existe"""
        try:
            venta = Venta.objects.get(id=value)
            if venta.estado == 'cancelada':
                raise serializers.ValidationError('No se puede pagar una venta cancelada')
            return value
        except Venta.DoesNotExist:
            raise serializers.ValidationError('La venta especificada no existe')
    
    def validate_monto(self, value):
        """Validar que el monto sea positivo"""
        if value and value <= 0:
            raise serializers.ValidationError('El monto debe ser mayor a 0')
        return value
