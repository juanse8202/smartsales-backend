from rest_framework import serializers
from catalogo.models import Catalogo, Producto

class CatalogoAuxSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Catalogo
        fields = ['id', 'sku', 'nombre', 'imagen_url', 'precio',
                'meses_garantia', 'modelo', 'marca', 'categoria', 'estado',
                'fecha_creacion']

class ProductoSerializer(serializers.ModelSerializer):
    catalogo = CatalogoAuxSerializer(read_only=True)
    catalogo_id = serializers.PrimaryKeyRelatedField(queryset=Catalogo.objects.all(), source='catalogo', write_only=True)
    
    catalogo = CatalogoAuxSerializer(read_only=True)
    catalogo_id = serializers.PrimaryKeyRelatedField(queryset=Catalogo.objects.all(), source='catalogo', write_only=True)
    class Meta:
        model = Producto
        fields = ['id', 'numero_serie', 'costo', 'fecha_venta','garantia_vigente',
                'fecha_fin_garantia','estado', 'fecha_ingreso',
                'catalogo', 'catalogo_id']
