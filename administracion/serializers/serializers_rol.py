from rest_framework import serializers
from django.contrib.auth.models import Group, Permission

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename']

class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        write_only=True,
        source='permissions'
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'permission_ids']

    def create(self, validated_data):
        # Obtener los permisos del validated_data
        permissions_data = validated_data.pop('permissions', [])
        
        # Crear el grupo
        group = Group.objects.create(**validated_data)
        
        # Asignar los permisos
        if permissions_data:
            group.permissions.set(permissions_data)
        
        return group

    def update(self, instance, validated_data):
        # Obtener los permisos del validated_data
        permissions_data = validated_data.pop('permissions', None)
        
        # Actualizar el grupo
        instance = super().update(instance, validated_data)
        
        # Actualizar los permisos si se proporcionaron
        if permissions_data is not None:
            instance.permissions.set(permissions_data)
        
        return instance