"""
ViewSet para gestión del Carrito de Compras
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from ventas.models import Cart, CartItem
from catalogo.models import Catalogo
from ventas.serializers.serializers_cart import CartSerializer, AddCartItemSerializer


class CartViewSet(viewsets.GenericViewSet):
    """
    ViewSet para gestión del carrito de compras
    """
    # permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_cart(self):
        """
        Obtiene o crea el carrito del usuario autenticado
        Requiere autenticación - cada usuario tiene su propio carrito
        """
        if not self.request.user.is_authenticated:
            return None
        
        user = self.request.user
        print(f"DEBUG get_cart - Usuario autenticado: {user.username} (ID: {user.id})")
        
        # Cada usuario autenticado tiene su propio carrito
        cart, created = Cart.objects.get_or_create(user=user)
        print(f"DEBUG get_cart - Cart ID: {cart.id}, Creado: {created}, Items: {cart.items.count()}")
        return cart

    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        """
        Ver mi carrito actual
        Ruta: GET /api/cart/my_cart/
        Requiere autenticación
        """
        if not request.user.is_authenticated:
            return Response({
                'items': [],
                'total_price': 0,
                'message': 'Debes iniciar sesión para ver tu carrito'
            }, status=status.HTTP_200_OK)
        
        cart = self.get_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], serializer_class=AddCartItemSerializer)
    def add_item(self, request):
        """
        Añadir un ítem al carrito.
        Ruta: POST /api/cart/add_item/
        Body: { "catalogo_id": 10, "quantity": 2 }
        Requiere autenticación
        """
        if not request.user.is_authenticated:
            return Response({
                'error': 'Debes iniciar sesión para agregar productos al carrito'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        cart = self.get_cart()
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        catalogo = get_object_or_404(Catalogo, pk=serializer.validated_data['catalogo_id'])
        quantity = serializer.validated_data['quantity']

        # Lógica de update_or_create
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            catalogo=catalogo,
            defaults={'quantity': quantity}
        )

        if not created:
            # Si ya existía, sumamos la cantidad
            cart_item.quantity += quantity
            cart_item.save()

        # Devolvemos el carrito actualizado completo
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='update_item/(?P<item_id>[^/.]+)')
    def update_item_quantity(self, request, item_id=None):
        """
        Actualizar la cantidad de un ítem específico.
        Ruta: PATCH /api/cart/update_item/{item_id}/
        Body: { "quantity": 5 }
        Requiere autenticación
        """
        if not request.user.is_authenticated:
            return Response({
                'error': 'Debes iniciar sesión para actualizar el carrito'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        cart = self.get_cart()
        # Aseguramos que el ítem pertenezca al carrito del usuario actual
        cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)

        quantity = int(request.data.get('quantity', 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            # Si envían cantidad 0 o menor, lo borramos
            cart_item.delete()

        return Response(CartSerializer(cart).data)

    @action(detail=False, methods=['delete'], url_path='remove_item/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """
        Eliminar un ítem del carrito.
        Ruta: DELETE /api/cart/remove_item/{item_id}/
        Requiere autenticación
        """
        if not request.user.is_authenticated:
            return Response({
                'error': 'Debes iniciar sesión para modificar el carrito'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        cart = self.get_cart()
        cart_item = get_object_or_404(CartItem, pk=item_id, cart=cart)
        cart_item.delete()
        
        return Response(CartSerializer(cart).data)
    
    @action(detail=False, methods=['post'])
    def clear_cart(self, request):
        """
        Vaciar completamente el carrito.
        Se llama cuando el pago es exitoso o al cerrar sesión.
        Ruta: POST /api/cart/clear_cart/
        Requiere autenticación
        """
        if not request.user.is_authenticated:
            return Response({
                'error': 'Debes iniciar sesión'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        cart = self.get_cart()
        cart.items.all().delete()
        
        return Response({
            'message': 'Carrito vaciado exitosamente',
            'cart': CartSerializer(cart).data
        })

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """
        Crear una venta a partir del carrito actual y vaciar el carrito
        Ruta: POST /api/cart/checkout/
        Body: {
            "cliente_id": 1,
            "direccion": "Calle Principal 123",
            "impuesto": 0.00,
            "descuento": 0.00,
            "costo_envio": 0.00
        }
        """
        from django.db import transaction
        from ventas.models import Venta, DetalleVenta
        from administracion.models import Cliente
        from administracion.core.utils import registrar_bitacora
        
        cart = self.get_cart()
        
        # Debug: Imprimir información del carrito
        print(f"DEBUG - Usuario: {request.user if request.user.is_authenticated else 'No autenticado'}")
        print(f"DEBUG - Cart ID: {cart.id}")
        print(f"DEBUG - Cantidad de items: {cart.items.count()}")
        print(f"DEBUG - Items: {list(cart.items.values_list('id', 'catalogo__nombre', 'quantity'))}")
        
        # Validar que el carrito no esté vacío
        if not cart.items.exists():
            return Response(
                {'error': 'El carrito está vacío'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener datos del request
        cliente_id = request.data.get('cliente_id')
        direccion = request.data.get('direccion', '')
        impuesto = float(request.data.get('impuesto', 0))
        descuento = float(request.data.get('descuento', 0))
        costo_envio = float(request.data.get('costo_envio', 0))
        
        # Validar cliente
        if not cliente_id:
            return Response(
                {'error': 'Debe proporcionar un cliente_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cliente = Cliente.objects.get(id=cliente_id, estado='activo')
        except Cliente.DoesNotExist:
            return Response(
                {'error': 'Cliente no encontrado o inactivo'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            with transaction.atomic():
                # Calcular subtotal del carrito
                subtotal = float(cart.total_price)
                
                # Calcular impuesto automáticamente (13% del subtotal)
                impuesto_calculado = subtotal * 0.13
                
                # Crear la venta
                venta = Venta.objects.create(
                    cliente=cliente,
                    subtotal=subtotal,
                    impuesto=impuesto_calculado,
                    descuento=descuento,
                    costo_envio=costo_envio,
                    direccion=direccion,
                    estado='pendiente'
                )
                
                # Crear los detalles de venta a partir de los items del carrito
                for item in cart.items.all():
                    DetalleVenta.objects.create(
                        venta=venta,
                        catalogo=item.catalogo,
                        cantidad=item.quantity,
                        precio_unitario=item.catalogo.precio,
                        descuento=0
                    )
                
                # NO vaciar el carrito aquí - se vaciará cuando el pago sea exitoso
                # El carrito se mantendrá para que el usuario pueda volver si cancela el pago
                
                # Registrar en bitácora
                registrar_bitacora(
                    request=request,
                    usuario=request.user if request.user.is_authenticated else None,
                    accion='CREAR',
                    descripcion=f'Venta #{venta.id} creada desde carrito para cliente {cliente.nombre}',
                    modulo='VENTAS'
                )
                
                # Retornar la venta creada
                from ventas.serializers.serializers_venta import VentaSerializer
                serializer = VentaSerializer(venta)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {'error': f'Error al crear la venta: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
