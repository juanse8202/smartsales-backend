"""
Vistas para gestionar pagos con Stripe
Implementación simplificada para proyecto universitario
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status, viewsets
from django.conf import settings
from django.shortcuts import get_object_or_404
from decimal import Decimal
import stripe
import logging

from ventas.models import Pago, Venta
from .serializers import (
    PagoStripeSerializer,
    PagoStripeCreateSerializer,
    PagoStripeListSerializer
)

# Configurar logging
logger = logging.getLogger(__name__)

# Configurar Stripe con la clave secreta
stripe.api_key = settings.STRIPE_SECRET_KEY


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def actualizar_stock_productos(venta):
    """
    Actualiza el stock de productos cuando se completa una venta.
    Marca productos como 'vendido' según la cantidad vendida.
    """
    from catalogo.models import Producto
    
    try:
        # Iterar sobre los detalles de la venta
        for detalle in venta.detalles.all():
            catalogo = detalle.catalogo
            cantidad_vendida = detalle.cantidad
            
            logger.info(f"📦 Actualizando stock: {catalogo.nombre} - Cantidad: {cantidad_vendida}")
            
            # Obtener productos disponibles del catálogo
            productos_disponibles = Producto.objects.filter(
                catalogo=catalogo,
                estado='disponible'
            ).order_by('fecha_ingreso')[:cantidad_vendida]
            
            # Marcar productos como vendidos
            productos_actualizados = 0
            for producto in productos_disponibles:
                producto.estado = 'vendido'
                producto.save(update_fields=['estado'])
                productos_actualizados += 1
                logger.info(f"✅ Producto {producto.numero_serie} marcado como vendido")
            
            if productos_actualizados < cantidad_vendida:
                logger.warning(f"⚠️ Solo se pudieron marcar {productos_actualizados}/{cantidad_vendida} productos como vendidos para {catalogo.nombre}")
            else:
                logger.info(f"✅ Stock actualizado: {productos_actualizados} productos de {catalogo.nombre} marcados como vendidos")
                
    except Exception as e:
        logger.error(f"❌ Error al actualizar stock: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


# ============================================
# VISTAS DE STRIPE PARA VENTAS
# ============================================

class CreatePaymentIntentVenta(APIView):
    """
    POST { 
        "venta_id": 123, 
        "monto": 500.00,  # Opcional, usa el total de la venta por defecto
        "moneda": "BOB",  # Opcional
        "descripcion": "..." 
    }
    -> Crea un PaymentIntent y devuelve { client_secret, payment_intent_id }
    Usar con Stripe Elements en el frontend (sin redirección).
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PagoStripeCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": "Datos inválidos", "detalles": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        venta_id = serializer.validated_data['venta_id']
        monto = serializer.validated_data.get('monto')
        moneda = serializer.validated_data.get('moneda', 'BOB')
        descripcion = serializer.validated_data.get('descripcion', '')
        
        # Obtener la venta
        venta = get_object_or_404(Venta, id=venta_id)
        
        # Verificar TODOS los pagos existentes para esta venta (no solo Stripe)
        pagos_existentes = Pago.objects.filter(venta=venta).order_by('-fecha_pago')
        
        # Si hay algún pago completado, no permitir crear otro
        pago_completado = pagos_existentes.filter(estado='completado').first()
        if pago_completado:
            logger.warning(f"⚠️ Venta #{venta.id} ya tiene un pago completado (Pago #{pago_completado.id})")
            return Response({
                "error": "Esta venta ya ha sido pagada",
                "pago_id": pago_completado.id,
                "venta_id": venta.id,
                "transaccion_id": pago_completado.transaccion_id
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Buscar pagos de Stripe pendientes
        pago_stripe_pendiente = pagos_existentes.filter(
            proveedor='Stripe',
            estado='pendiente'
        ).first()
        
        if pago_stripe_pendiente:
            # Si hay un pago pendiente, intentar reutilizarlo
            try:
                # Recuperar el Payment Intent de Stripe para obtener el client_secret
                pi = stripe.PaymentIntent.retrieve(pago_stripe_pendiente.transaccion_id)
                
                # Solo reutilizar si el Payment Intent aún está en estado pendiente
                if pi.status in ['requires_payment_method', 'requires_confirmation', 'requires_action']:
                    logger.info(f"♻️ Reutilizando Payment Intent {pi.id} para venta #{venta.id}")
                    
                    return Response({
                        "client_secret": pi.client_secret,
                        "payment_intent_id": pi.id,
                        "pago_id": pago_stripe_pendiente.id,
                        "monto": float(pago_stripe_pendiente.monto),
                        "moneda": pago_stripe_pendiente.moneda,
                        "venta_id": venta.id,
                        "reutilizado": True
                    }, status=status.HTTP_200_OK)
                else:
                    # Si el Payment Intent ya se procesó (succeeded, canceled, etc), eliminarlo
                    logger.warning(f"⚠️ Payment Intent {pi.id} en estado {pi.status}, limpiando...")
                    if pi.status == 'succeeded':
                        # Si ya se procesó exitosamente, marcar el pago como completado
                        pago_stripe_pendiente.estado = 'completado'
                        pago_stripe_pendiente.save()
                        return Response({
                            "error": "Este pago ya fue procesado exitosamente",
                            "pago_id": pago_stripe_pendiente.id
                        }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # Cancelar y eliminar registros obsoletos
                        if pi.status == 'requires_capture':
                            stripe.PaymentIntent.cancel(pi.id)
                        pago_stripe_pendiente.delete()
                    
            except stripe.error.InvalidRequestError:
                # Si el Payment Intent no existe en Stripe, eliminar el registro local
                logger.warning(f"⚠️ Payment Intent {pago_stripe_pendiente.transaccion_id} no existe en Stripe, eliminando")
                pago_stripe_pendiente.delete()
            except stripe.StripeError as e:
                logger.error(f"❌ Error al recuperar Payment Intent: {str(e)}")
                # Eliminar el registro problemático
                pago_stripe_pendiente.delete()
        
        # Usar el monto proporcionado o el total de la venta
        if not monto:
            monto = venta.total
        
        monto = Decimal(str(monto))
        
        if monto <= 0:
            return Response(
                {"error": "El monto debe ser mayor a 0"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convertir a centavos (Stripe usa centavos)
        amount_cents = int(monto * 100)
        
        # Idempotencia: agregar timestamp para permitir múltiples intentos
        import time
        idem_key = f"pi-venta-{venta.id}-{int(time.time())}"
        
        logger.info(f"📤 Creando nuevo Payment Intent para venta #{venta.id}, monto: {moneda} {monto}")
        
        try:
            # Mapear monedas
            currency_map = {
                'BOB': 'bob',
                'USD': 'usd',
                'EUR': 'eur'
            }
            stripe_currency = currency_map.get(moneda, 'bob')
            
            # Crear Payment Intent en Stripe
            pi = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=stripe_currency,
                metadata={
                    "venta_id": str(venta.id),
                    "cliente_id": str(venta.cliente.id),
                    "cliente_nombre": venta.cliente.nombre
                },
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never"  # Evitar métodos que requieren return_url
                },
                idempotency_key=idem_key,
                description=descripcion or f"Pago de Venta #{venta.id} - Cliente: {venta.cliente.nombre}"
            )
            
            # Guardar el Payment Intent ID en un nuevo registro de Pago
            pago = Pago.objects.create(
                venta=venta,
                monto=monto,
                moneda=moneda,
                estado='pendiente',
                proveedor='Stripe',
                transaccion_id=pi.id
            )
            
            logger.info(f"✅ Payment Intent {pi.id} creado. Pago ID: {pago.id}")
            
            return Response({
                "client_secret": pi.client_secret,
                "payment_intent_id": pi.id,
                "pago_id": pago.id,
                "monto": float(monto),
                "moneda": moneda,
                "venta_id": venta.id
            }, status=status.HTTP_201_CREATED)
            
        except stripe.StripeError as stripe_error:
            error_message = str(stripe_error)
            logger.error(f"❌ Error de Stripe: {error_message}")
            return Response(
                {"error": f"Error con Stripe: {error_message}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Error inesperado: {error_message}")
            import traceback
            logger.error(traceback.format_exc())
            return Response(
                {"error": f"Error interno: {error_message}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfirmPaymentAutoVenta(APIView):
    """
    POST { "payment_intent_id": "pi_xxx" }
    -> Confirma el Payment Intent automáticamente usando Payment Method de prueba
    SOLO PARA DESARROLLO Y PRUEBAS
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        pi_id = request.data.get("payment_intent_id")
        
        if not pi_id:
            return Response(
                {"error": "payment_intent_id requerido"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            logger.info(f"🔄 Confirmando Payment Intent automáticamente: {pi_id}")
            
            # Usar el Payment Method de prueba predefinido de Stripe
            TEST_PAYMENT_METHOD = "pm_card_visa"
            
            logger.info(f"💳 Usando Payment Method de prueba: {TEST_PAYMENT_METHOD}")
            
            # Confirmar el Payment Intent
            pi = stripe.PaymentIntent.confirm(
                pi_id,
                payment_method=TEST_PAYMENT_METHOD,
            )
            
            status_pi = pi.get("status")
            logger.info(f"✅ Payment Intent confirmado: {status_pi}")
            
            return Response({
                "success": True,
                "status": status_pi,
                "payment_intent_id": pi_id,
                "message": "Pago confirmado automáticamente con tarjeta de prueba"
            }, status=status.HTTP_200_OK)
            
        except stripe.StripeError as e:
            error_message = str(e)
            logger.error(f"❌ Error de Stripe: {error_message}")
            return Response(
                {"error": f"Error de Stripe: {error_message}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Error: {error_message}")
            import traceback
            logger.error(traceback.format_exc())
            
            return Response(
                {"error": f"Error al confirmar pago: {error_message}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfirmPaymentWithCardVenta(APIView):
    """
    POST { 
        "payment_intent_id": "pi_xxx",
        "payment_method_id": "pm_card_visa"  # Payment Method de prueba o real
    }
    -> Confirma el Payment Intent con un Payment Method específico
    
    Payment Methods de prueba comunes:
    - pm_card_visa: Visa exitosa
    - pm_card_mastercard: Mastercard exitosa
    - pm_card_amex: American Express exitosa
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        pi_id = request.data.get("payment_intent_id")
        payment_method_id = request.data.get("payment_method_id")
        card_number = request.data.get("card_number", "").replace(" ", "")
        
        if not pi_id:
            return Response(
                {"error": "payment_intent_id requerido"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mapear números de tarjeta de prueba a payment methods
        if not payment_method_id and card_number:
            test_cards = {
                "4242424242424242": "pm_card_visa",
                "5555555555554444": "pm_card_mastercard",
                "378282246310005": "pm_card_amex",
            }
            
            if card_number in test_cards:
                payment_method_id = test_cards[card_number]
                logger.info(f"💳 Mapeando tarjeta de prueba a: {payment_method_id}")
            else:
                return Response(
                    {
                        "error": "Para pruebas, usa payment_method_id o una tarjeta de prueba válida",
                        "test_cards": list(test_cards.keys()),
                        "test_payment_methods": list(test_cards.values())
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if not payment_method_id:
            return Response(
                {"error": "payment_method_id o card_number requerido"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            logger.info(f"🔄 Procesando pago para Payment Intent: {pi_id}")
            logger.info(f"💳 Payment Method: {payment_method_id}")
            
            # Confirmar el Payment Intent
            pi = stripe.PaymentIntent.confirm(
                pi_id,
                payment_method=payment_method_id,
            )
            
            status_pi = pi.get("status")
            logger.info(f"✅ Payment Intent confirmado: {status_pi}")
            
            # Si el pago fue exitoso, actualizar el registro en BD
            if status_pi == "succeeded":
                pago = Pago.objects.filter(transaccion_id=pi_id).first()
                if pago:
                    pago.estado = 'completado'
                    pago.save(update_fields=['estado'])
                    
                    # Actualizar estado de la venta
                    if pago.venta:
                        pago.venta.estado = 'completada'
                        pago.venta.save(update_fields=['estado'])
                        logger.info(f"✅ Venta #{pago.venta.id} marcada como completada")
                        
                        # Actualizar stock de productos (marcar como vendidos)
                        actualizar_stock_productos(pago.venta)
                    
                    logger.info(f"✅ Pago #{pago.id} marcado como completado")
            
            return Response({
                "success": True,
                "status": status_pi,
                "payment_intent_id": pi_id,
                "payment_method_id": payment_method_id,
                "message": "Pago procesado exitosamente"
            }, status=status.HTTP_200_OK)
            
        except stripe.StripeError as e:
            error_message = getattr(e, 'user_message', None) or str(e)
            logger.error(f"❌ Error de Stripe: {error_message}")
            
            return Response(
                {"error": f"Error de Stripe: {error_message}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Error: {error_message}")
            import traceback
            logger.error(traceback.format_exc())
            
            return Response(
                {"error": f"Error al procesar pago: {error_message}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyPaymentIntentVenta(APIView):
    """
    POST { "payment_intent_id": "pi_xxx" }
    -> Devuelve estado del PaymentIntent y actualiza el pago si 'succeeded'
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        pi_id = request.data.get("payment_intent_id")
        
        if not pi_id:
            return Response(
                {"error": "payment_intent_id requerido"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            logger.info(f"🔍 Verificando Payment Intent: {pi_id}")
            
            # Recuperar Payment Intent de Stripe
            pi = stripe.PaymentIntent.retrieve(pi_id)
            status_pi = pi.get("status")
            metadata = pi.get("metadata") or {}
            venta_id = metadata.get("venta_id")
            
            logger.info(f"📊 Estado del Payment Intent: {status_pi}")
            
            # Buscar el pago por Transaction ID
            pago = Pago.objects.filter(transaccion_id=pi_id).first()
            
            if not pago:
                logger.error(f"❌ No se encontró el pago con Payment Intent: {pi_id}")
                return Response({
                    "error": "Pago no encontrado en la base de datos",
                    "payment_intent_id": pi_id,
                    "status": status_pi
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Si el pago fue exitoso, actualizar
            if status_pi == "succeeded" and pago.estado != 'completado':
                pago.estado = 'completado'
                pago.save(update_fields=['estado'])
                
                # Actualizar estado de la venta
                if pago.venta and pago.venta.estado != 'completada':
                    pago.venta.estado = 'completada'
                    pago.venta.save(update_fields=['estado'])
                    logger.info(f"✅ Venta #{pago.venta.id} marcada como completada")
                    
                    # Actualizar stock de productos (marcar como vendidos)
                    actualizar_stock_productos(pago.venta)
                
                logger.info(f"✅ Pago #{pago.id} confirmado exitosamente")
            
            elif status_pi == "canceled":
                pago.estado = 'fallido'
                pago.save(update_fields=['estado'])
            
            # Serializar el pago
            pago_data = PagoStripeSerializer(pago).data
            
            return Response({
                "status": status_pi,
                "venta_id": venta_id,
                "pago": pago_data,
                "message": f"Pago en estado: {status_pi}"
            }, status=status.HTTP_200_OK)
            
        except stripe.StripeError as e:
            error_message = str(e)
            logger.error(f"❌ Error de Stripe: {error_message}")
            return Response(
                {"error": f"Error de Stripe: {error_message}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Error: {error_message}")
            import traceback
            logger.error(traceback.format_exc())
            
            return Response(
                {"error": f"Error al procesar: {error_message}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================
# VIEWSET PARA CONSULTAR PAGOS
# ============================================

class MisPagosView(APIView):
    """
    Vista para obtener solo los pagos del usuario autenticado
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Retorna solo los pagos del usuario autenticado"""
        from administracion.models import Cliente
        
        # Obtener el cliente asociado al usuario autenticado
        try:
            cliente = Cliente.objects.filter(usuario=request.user).first()
        except Cliente.DoesNotExist:
            return Response({
                'error': 'No tienes un cliente asociado',
                'results': []
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Obtener pagos del cliente - SOLO COMPLETADOS
        queryset = Pago.objects.filter(
            venta__cliente=cliente,
            estado='completado'  # Solo pagos completados
        ).select_related('venta', 'venta__cliente')
        
        # Filtro opcional por venta_id
        venta_id = request.query_params.get('venta', None)
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)
        
        # Ordenar por fecha descendente
        queryset = queryset.order_by('-fecha_pago')
        
        # Serializar
        serializer = PagoStripeListSerializer(queryset, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


class PagoStripeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para consultar pagos realizados (Admin)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Retorna pagos filtrados"""
        queryset = Pago.objects.select_related('venta', 'venta__cliente')
        
        # Filtros por query params
        venta_id = self.request.query_params.get('venta', None)
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)
        
        # Filtro por nombre de cliente
        cliente = self.request.query_params.get('cliente', None)
        if cliente:
            queryset = queryset.filter(venta__cliente__nombre__icontains=cliente)
        
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)
        
        proveedor = self.request.query_params.get('proveedor', None)
        if proveedor:
            queryset = queryset.filter(proveedor__icontains=proveedor)
        
        return queryset.order_by('-fecha_pago')
    
    def get_serializer_class(self):
        """Retorna el serializer según la acción"""
        if self.action == 'list':
            return PagoStripeListSerializer
        return PagoStripeSerializer
