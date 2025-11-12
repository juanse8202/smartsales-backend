from rest_framework import serializers
from django.contrib.auth.models import User, Group

class GroupAuxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'role_id']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['password'].required = False

    def get_role(self, obj):
        """Obtiene el rol del usuario de manera segura"""
        first_group = obj.groups.first()
        return first_group.name if first_group else None

    def validate_username(self, value):
        if " " in value:
            raise serializers.ValidationError("El nombre de usuario no puede tener espacios.")
        if len(value) < 3:
            raise serializers.ValidationError("El nombre de usuario debe tener al menos 3 caracteres.")
        return value

    def validate_email(self, value):
        # Excluir el usuario actual en caso de actualización
        if self.instance:
            if User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("Este email ya está en uso.")
        else:
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("Este email ya está en uso.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("La contraseña debe contener al menos un número.")
        if not any(char.isalpha() for char in value):
            raise serializers.ValidationError("La contraseña debe contener al menos una letra.")
        return value

    def validate(self, data):
        """Validación a nivel de serializer"""
        # Al crear un usuario, el rol es obligatorio
        if not self.instance and not data.get('role_id'):
            raise serializers.ValidationError({
                'role_id': 'Debe asignar un rol al usuario.'
            })
        return data

    def create(self, validated_data):
        group_data = validated_data.pop('role_id', None)
        user = User.objects.create_user(**validated_data)
        if group_data:
            user.groups.set([group_data])
        return user

    def update(self, instance, validated_data):
        group_data = validated_data.pop('role_id', None)
        if 'password' in validated_data:
            instance.set_password(validated_data.pop('password'))
        instance = super().update(instance, validated_data)
        if group_data is not None:
            instance.groups.set([group_data])
        return instance