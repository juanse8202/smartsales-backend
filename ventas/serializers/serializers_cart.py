from rest_framework import serializers
from ..models import Cart, CartItem
from catalogo.serializers.serializers_catalogo import CatalogoSerializer # Asegúrate de tener esto

class CartItemSerializer(serializers.ModelSerializer):
    # Anidamos el serializador de Catalogo para mostrar todos sus detalles (nombre, imagen, precio, etc.)
    # read_only=True porque no queremos que editen el catálogo desde el carrito.
    catalogo = CatalogoSerializer(read_only=True)
    
    # Estos campos son calculados o de solo lectura
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'catalogo', 'quantity', 'subtotal']

class CartSerializer(serializers.ModelSerializer):
    # Reutilizamos el CartItemSerializer para mostrar los ítems dentro del carrito
    items = CartItemSerializer(many=True, read_only=True)
    
    # Campo calculado para el total de todo el carrito
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'created_at', 'updated_at']
        # No incluimos 'user' porque generalmente el usuario sabe quién es él mismo.

class AddCartItemSerializer(serializers.ModelSerializer):
    # El cliente envía el ID del catálogo y la cantidad que quiere
    catalogo_id = serializers.IntegerField(write_only=True) # write_only para que no salga en las respuestas GET
    quantity = serializers.IntegerField(default=1)

    class Meta:
        model = CartItem
        fields = ['catalogo_id', 'quantity']

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("La cantidad debe ser al menos 1.")
        return value
    
    # Aquí podrías agregar la validación de stock si quieres ser muy pro:
    # def validate_catalogo_id(self, value): ...