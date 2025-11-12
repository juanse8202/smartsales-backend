from rest_framework import serializers
from catalogo.models import Categoria, Marca, Catalogo

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre']

class CatalogoSerializer(serializers.ModelSerializer):
    marca = MarcaSerializer(read_only=True)
    categoria = CategoriaSerializer(read_only=True)
    marca_id = serializers.PrimaryKeyRelatedField(queryset=Marca.objects.all(), source='marca', write_only=True, allow_null=True, required=False)
    categoria_id = serializers.PrimaryKeyRelatedField(queryset=Categoria.objects.all(), source='categoria', write_only=True, allow_null=True, required=False)
    
    stock_disponible = serializers.SerializerMethodField()

    class Meta:
        model = Catalogo

        fields = ['id', 'sku', 'nombre', 'descripcion', 'imagen_url', 'precio',
                'meses_garantia', 'modelo', 'marca', 'categoria', 'estado',
                'stock_disponible', 'fecha_creacion', 'marca_id', 'categoria_id']
        read_only_fields = ['fecha_creacion', 'marca', 'categoria', 'stock_disponible'] 

    def get_stock_disponible(self, obj):
        return obj.stock_disponible
