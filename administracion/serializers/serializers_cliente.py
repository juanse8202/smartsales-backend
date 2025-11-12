from rest_framework import serializers
from administracion.models import Cliente, Departamento, Ciudad

class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id', 'nombre']

class CiudadSerializer(serializers.ModelSerializer):
    departamento = DepartamentoSerializer(read_only=True)
    
    departamento_id = serializers.PrimaryKeyRelatedField(
        queryset=Departamento.objects.all(),  
        source='departamento',  
        write_only=True
    )

    class Meta:
        model = Ciudad
        fields = [
            'id', 'nombre', 
            'departamento',     
            'departamento_id'   
        ]

class ClienteSerializer(serializers.ModelSerializer):
    ciudad = CiudadSerializer(read_only=True)
    
    ciudad_id = serializers.PrimaryKeyRelatedField(
        queryset=Ciudad.objects.all(), 
        source='ciudad',
        write_only=True
    )

    class Meta:
        model = Cliente
        fields = [
            'id', 'nombre', 'telefono', 
            'ciudad',     
            'ciudad_id',       
            'razon_social', 'sexo', 'estado', 
            'fecha_registro', 'usuario', 'nit_ci'
        ]
        read_only_fields = ['fecha_registro']