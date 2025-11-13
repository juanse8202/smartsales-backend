from rest_framework import serializers
from administracion.models import RegistroBitacora
from django.utils import timezone

class RegistroBitacoraSerializer(serializers.ModelSerializer):
    usuario_username = serializers.SerializerMethodField(read_only=True)
    fecha_hora_formateada = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = RegistroBitacora
        fields = [
            'id',
            'usuario_username',
            'accion',
            'descripcion',
            'modulo',
            'ip_address',
            'fecha_hora',
            'fecha_hora_formateada',
        ]
        read_only_fields = [
            'id',
            'accion',
            'descripcion',
            'modulo',
            'ip_address',
            'fecha_hora',
        ]
    
    def get_usuario_username(self, obj):
        return obj.usuario.username if obj.usuario else "Sistema"
    
    def get_fecha_hora_formateada(self, obj):
        local_fecha = timezone.localtime(obj.fecha_hora)
        return local_fecha.strftime("%d/%m/%Y %H:%M:%S")