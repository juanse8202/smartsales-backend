from django.db.models import ProtectedError
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.contrib.auth.models import User, Group, Permission
from .serializers.serializers_usuario import UserSerializer
from .serializers.serializers_rol import RoleSerializer, PermissionSerializer
from .serializers.serializers_cliente import ClienteSerializer, CiudadSerializer, DepartamentoSerializer
from administracion.models import Departamento, Ciudad, Cliente, RegistroBitacora
from .serializers.serializers_bitacora import RegistroBitacoraSerializer
from .core.utils import registrar_bitacora
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt 
from rest_framework.views import APIView
from django.contrib.auth.hashers import check_password

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication


# ==================== VISTAS DE AUTENTICACIÓN ====================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extiende el serializer por defecto para añadir datos del usuario
    tanto al token como a la respuesta JSON del login.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Añade campos personalizados dentro del payload del token
        token["username"] = user.username
        token["email"] = getattr(user, "email", "")
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Buscar el cliente asociado al usuario
        cliente = Cliente.objects.filter(usuario=self.user).first()
        cliente_id = cliente.id if cliente else None
        
        # Añade información del usuario a la respuesta del endpoint de login
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": getattr(self.user, "email", ""),
            "is_staff": self.user.is_staff,
            "cliente_id": cliente_id,
        }
        
        # Registrar login en bitácora
        from .core.utils import registrar_bitacora
        registrar_bitacora(
            request=self.context.get('request'),
            usuario=self.user,
            accion="LOGIN",
            descripcion=f"Usuario '{self.user.username}' inició sesión exitosamente",
            modulo="Autenticacion"
        )
        
        return data


@method_decorator(csrf_exempt, name="dispatch")
class CustomTokenObtainPairView(TokenObtainPairView):
    """Vista de login que usa el serializer personalizado.

    - Permite peticiones desde el frontend (AllowAny).
    - No usa autenticación previa (authentication_classes vacías) para permitir login.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class LogoutView(APIView):
    """Cierra sesión invalidando (blacklist) el refresh token.

    Body esperado: { "refresh": "<refresh_token>" }
    Requiere que la app 'rest_framework_simplejwt.token_blacklist' esté en INSTALLED_APPS
    y que se hayan corrido las migraciones.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            # Registrar logout en bitácora
            registrar_bitacora(
                request=request,
                usuario=request.user,
                accion="LOGOUT",
                descripcion=f"Usuario '{request.user.username}' cerró sesión",
                modulo="Autenticacion"
            )
            
            return Response({"message": "Logout exitoso"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    """Vista pública para registrar nuevos usuarios.
    
    No requiere autenticación. Crea usuario y devuelve tokens JWT automáticamente.
    Body esperado: { "username": "...", "email": "...", "password": "...", "password_confirm": "..." }
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # Validar datos requeridos
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')

        if not all([username, email, password, password_confirm]):
            return Response(
                {"error": "Todos los campos son requeridos: username, email, password, password_confirm"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que las contraseñas coincidan
        if password != password_confirm:
            return Response(
                {"error": "Las contraseñas no coinciden"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar longitud de contraseña
        if len(password) < 8:
            return Response(
                {"error": "La contraseña debe tener al menos 8 caracteres"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si el usuario ya existe
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "El nombre de usuario ya está en uso"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si el email ya existe
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "El email ya está en uso"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Crear el usuario (sin cliente automático)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Registrar en bitácora
            registrar_bitacora(
                request=request,
                usuario=user,
                accion="REGISTRO",
                descripcion=f"Nuevo usuario registrado: '{user.username}' con email '{user.email}'. Cliente pendiente de completar datos.",
                modulo="Autenticacion"
            )

            # Generar tokens JWT
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": "Usuario registrado exitosamente. Complete los datos del cliente.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_staff": user.is_staff,
                    "cliente_id": None,  # Sin cliente aún
                },
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"Error al crear el usuario: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProfileView(APIView):
    """Vista para ver y editar el perfil del usuario autenticado.
    
    GET: Obtiene información del perfil actual
    PUT/PATCH: Actualiza información del perfil (username, email, first_name, last_name)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Buscar el cliente asociado al usuario
        cliente = Cliente.objects.filter(usuario=user).first()
        cliente_id = cliente.id if cliente else None
        
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "date_joined": user.date_joined,
            "cliente_id": cliente_id,
        })

    def put(self, request):
        user = request.user
        data = request.data

        # Validar si username está disponible (si se cambió)
        new_username = data.get('username', user.username)
        if new_username != user.username and User.objects.filter(username=new_username).exists():
            return Response(
                {"error": "El nombre de usuario ya está en uso"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar si email está disponible (si se cambió)
        new_email = data.get('email', user.email)
        if new_email != user.email and User.objects.filter(email=new_email).exists():
            return Response(
                {"error": "El email ya está en uso"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Actualizar campos
        user.username = new_username
        user.email = new_email
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.save()

        # Registrar en bitácora
        registrar_bitacora(
            request=request,
            usuario=user,
            accion="EDITAR PERFIL",
            descripcion=f"Usuario '{user.username}' actualizó su perfil",
            modulo="Administracion"
        )

        return Response({
            "message": "Perfil actualizado exitosamente",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        })


class ChangePasswordView(APIView):
    """Vista para cambiar la contraseña del usuario autenticado.
    
    Body esperado: {
        "old_password": "contraseña_actual",
        "new_password": "nueva_contraseña",
        "new_password_confirm": "nueva_contraseña"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        new_password_confirm = request.data.get('new_password_confirm')

        # Validar campos requeridos
        if not all([old_password, new_password, new_password_confirm]):
            return Response(
                {"error": "Todos los campos son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar contraseña actual
        if not check_password(old_password, user.password):
            return Response(
                {"error": "La contraseña actual es incorrecta"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que las nuevas contraseñas coincidan
        if new_password != new_password_confirm:
            return Response(
                {"error": "Las contraseñas nuevas no coinciden"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar longitud de contraseña
        if len(new_password) < 8:
            return Response(
                {"error": "La contraseña debe tener al menos 8 caracteres"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cambiar contraseña
        user.set_password(new_password)
        user.save()

        # Registrar en bitácora
        registrar_bitacora(
            request=request,
            usuario=user,
            accion="CAMBIAR CONTRASEÑA",
            descripcion=f"Usuario '{user.username}' cambió su contraseña",
            modulo="Administracion"
        )

        return Response({
            "message": "Contraseña actualizada exitosamente"
        }, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        rol_info = instance.groups.first()
        rol_nombre = rol_info.name if rol_info else 'Sin rol'
        descripcion = f"Usuario '{instance.username}' creado con email '{instance.email}' y rol '{rol_nombre}'"
        registrar_bitacora(
                request=self.request, 
                usuario=self.request.user, 
                accion="CREAR", 
                descripcion=descripcion,
                modulo="Administracion"
        )
    
    def perform_update(self, serializer):
        instance = self.get_object()
        username_original = instance.username
        email_original = instance.email
        rol_original = instance.groups.first()
        rol_original_nombre = rol_original.name if rol_original else 'Sin rol'
        instance = serializer.save()
        rol_nuevo = instance.groups.first()
        rol_nuevo_nombre = rol_nuevo.name if rol_nuevo else 'Sin rol'
        cambios = []
        if instance.username != username_original:
            cambios.append(f"username: '{username_original}' → '{instance.username}'")
        if instance.email != email_original:
            cambios.append(f"email: '{email_original}' → '{instance.email}'")
        if rol_original_nombre != rol_nuevo_nombre:
            cambios.append(f"rol: '{rol_original_nombre}' → '{rol_nuevo_nombre}'")
        
        descripcion = f"Usuario '{instance.username}' actualizado"
        if cambios:
            descripcion += f". Cambios: {', '.join(cambios)}"
        else:
            descripcion += ". Sin cambios detectados"
        
        registrar_bitacora(
            request=request, 
            usuario=self.request.user, 
            accion="EDITAR", 
            descripcion=descripcion,
            modulo="Administracion"
        )
    
    def perform_destroy(self, instance):
        username_usuario = instance.username
        email_usuario = instance.email
        rol_info = instance.groups.first()
        rol_nombre = rol_info.name if rol_info else 'Sin rol'
        instance.delete()
        descripcion = f"Usuario '{username_usuario}' eliminado. Tenía email '{email_usuario}' y rol '{rol_nombre}'"
        registrar_bitacora(
            request=self.request, 
            usuario=self.request.user, 
            accion="ELIMINAR", 
            descripcion=descripcion,
            modulo="Administracion"
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {"detail": "No se puede eliminar este usuario porque está asociado a otros registros (como un cliente o empleado)."},
                status=status.HTTP_400_BAD_REQUEST
            )

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = RoleSerializer
    
    def perform_create(self, serializer):
        """Crear rol y registrar en bitácora"""
        # Ejecutar la creación original
        instance = serializer.save()
        
        # Registrar en bitácora
        permisos_info = [perm.name for perm in instance.permissions.all()]
        descripcion = f"Rol '{instance.name}' creado con permisos: {', '.join(permisos_info) if permisos_info else 'Sin permisos'}"
        
        registrar_bitacora(
                request=self.request, 
                usuario=self.request.user, 
                accion="CREAR", 
                descripcion=descripcion,
                modulo="Administracion"
        )
    
    def perform_update(self, serializer):
        """Actualizar rol y registrar en bitácora"""
        # Guardar datos originales para comparación
        instance = self.get_object()
        nombre_original = instance.name
        permisos_originales = set(instance.permissions.values_list('name', flat=True))
        
        # Ejecutar la actualización original
        instance = serializer.save()
        
        # Obtener nuevos permisos
        permisos_nuevos = set(instance.permissions.values_list('name', flat=True))
        
        # Crear descripción detallada
        permisos_agregados = permisos_nuevos - permisos_originales
        permisos_removidos = permisos_originales - permisos_nuevos
        
        descripcion = f"Rol '{instance.name}' actualizado"
        if permisos_agregados:
            descripcion += f". Permisos agregados: {', '.join(permisos_agregados)}"
        if permisos_removidos:
            descripcion += f". Permisos removidos: {', '.join(permisos_removidos)}"
        if not permisos_agregados and not permisos_removidos:
            descripcion += ". Sin cambios en permisos"
        
        registrar_bitacora(
                request=self.request, 
                usuario=self.request.user, 
                accion="EDITAR", 
                descripcion=descripcion,
                modulo="Administracion"
        )
    
    def perform_destroy(self, instance):
        """Eliminar rol y registrar en bitácora"""
        # Guardar información antes de eliminar
        nombre_rol = instance.name
        permisos_info = [perm.name for perm in instance.permissions.all()]
        
        # Ejecutar la eliminación original
        instance.delete()
        
        # Registrar en bitácora
        descripcion = f"Rol '{nombre_rol}' eliminado. Tenía permisos: {', '.join(permisos_info) if permisos_info else 'Sin permisos'}"
        
        registrar_bitacora(
                request=self.request, 
                usuario=self.request.user, 
                accion="ELIMINAR", 
                descripcion=descripcion,
                modulo="Administracion"
        )

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer

class DepartamentoViewSet(viewsets.ModelViewSet):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer

class CiudadViewSet(viewsets.ModelViewSet):
    queryset = Ciudad.objects.all()
    serializer_class = CiudadSerializer
    
    def get_queryset(self):
        """Filtrar ciudades por departamento si se especifica en la query"""
        queryset = Ciudad.objects.all()
        departamento_id = self.request.query_params.get('departamento', None)
        
        if departamento_id is not None:
            queryset = queryset.filter(departamento_id=departamento_id)
        
        return queryset

class MiClienteView(APIView):
    """Vista para obtener, crear y actualizar el cliente asociado al usuario autenticado.
    
    GET: Devuelve el cliente asociado (null si no existe)
    POST: Crea el cliente con los datos proporcionados (solo si no existe)
    PUT: Actualiza los datos del cliente
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtener cliente asociado al usuario (sin crearlo automáticamente)"""
        user = request.user
        
        # Buscar el cliente asociado al usuario
        cliente = Cliente.objects.filter(usuario=user).first()
        
        if not cliente:
            return Response({
                "cliente_id": None,
                "message": "No tienes un perfil de cliente. Completa tus datos para crear uno."
            }, status=status.HTTP_200_OK)
        
        serializer = ClienteSerializer(cliente)
        return Response(serializer.data)
    
    def post(self, request):
        """Crear cliente asociado al usuario con datos completos"""
        user = request.user
        
        # Verificar si ya tiene un cliente
        if Cliente.objects.filter(usuario=user).exists():
            return Response(
                {"error": "Ya tienes un perfil de cliente asociado"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar datos requeridos
        nombre = request.data.get('nombre')
        nit_ci = request.data.get('nit_ci')
        telefono = request.data.get('telefono')
        razon_social = request.data.get('razon_social', 'natural')
        
        if not all([nombre, nit_ci, telefono]):
            return Response(
                {"error": "Los campos nombre, nit_ci y telefono son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Obtener ciudad y departamento
            ciudad_id = request.data.get('ciudad')
            departamento_id = request.data.get('departamento')
            
            ciudad = None
            departamento = None
            
            if ciudad_id:
                ciudad = Ciudad.objects.filter(id=ciudad_id).first()
            if departamento_id:
                departamento = Departamento.objects.filter(id=departamento_id).first()
            
            # Crear el cliente
            cliente = Cliente.objects.create(
                nombre=nombre,
                nit_ci=nit_ci,
                telefono=telefono,
                email=request.data.get('email', user.email),
                direccion=request.data.get('direccion', ''),
                razon_social=razon_social,
                sexo=request.data.get('sexo', ''),
                estado=request.data.get('estado', 'activo'),
                usuario=user,
                ciudad=ciudad,
                departamento=departamento
            )
            
            # Registrar en bitácora
            registrar_bitacora(
                request=request,
                usuario=user,
                accion="COMPLETAR PERFIL",
                descripcion=f"Usuario '{user.username}' completó su perfil de cliente (ID: {cliente.id})",
                modulo="Clientes"
            )
            
            serializer = ClienteSerializer(cliente)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": f"Error al crear perfil de cliente: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request):
        """Actualizar datos del cliente asociado al usuario"""
        user = request.user
        
        # Buscar el cliente asociado
        cliente = Cliente.objects.filter(usuario=user).first()
        
        if not cliente:
            return Response(
                {"error": "No tienes un perfil de cliente asociado"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Obtener datos del request
        data = request.data.copy()
        
        # Actualizar campos del cliente
        if 'nombre' in data:
            cliente.nombre = data['nombre']
        if 'email' in data:
            cliente.email = data['email']
        if 'telefono' in data:
            cliente.telefono = data['telefono']
        if 'direccion' in data:
            cliente.direccion = data['direccion']
        if 'nit' in data:
            cliente.nit_ci = data['nit']
        
        try:
            cliente.save()
            
            # Registrar en bitácora
            registrar_bitacora(
                request=request,
                usuario=user,
                accion="ACTUALIZAR PERFIL",
                descripcion=f"Usuario '{user.username}' actualizó su perfil de cliente",
                modulo="Clientes"
            )
            
            serializer = ClienteSerializer(cliente)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Error al actualizar perfil: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CambiarContrasenaView(APIView):
    """Vista para cambiar la contraseña del usuario autenticado.
    
    POST: Cambia la contraseña del usuario
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        # Validaciones
        if not current_password or not new_password:
            return Response(
                {"error": "Debes proporcionar la contraseña actual y la nueva contraseña"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar contraseña actual
        if not user.check_password(current_password):
            return Response(
                {"error": "La contraseña actual es incorrecta"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar longitud de nueva contraseña
        if len(new_password) < 8:
            return Response(
                {"error": "La nueva contraseña debe tener al menos 8 caracteres"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que la nueva contraseña sea diferente
        if current_password == new_password:
            return Response(
                {"error": "La nueva contraseña debe ser diferente a la actual"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Cambiar contraseña
            user.set_password(new_password)
            user.save()
            
            # Registrar en bitácora
            registrar_bitacora(
                request=request,
                usuario=user,
                accion="CAMBIAR CONTRASEÑA",
                descripcion=f"Usuario '{user.username}' cambió su contraseña",
                modulo="Seguridad"
            )
            
            return Response(
                {"message": "Contraseña cambiada exitosamente"},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": f"Error al cambiar contraseña: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    
    def perform_create(self, serializer):
        cliente_guardado = serializer.save(usuario=self.request.user)
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="CREAR CLIENTE",
            descripcion=f"Se creó el cliente: {cliente_guardado.nombre}",
            modulo="Clientes"
        )
    
    def perform_update(self, serializer):
        cliente_original = self.get_object()
        nombre_original = cliente_original.nombre
        
        cliente_actualizado = serializer.save()
        
        cambios = []
        if cliente_actualizado.nombre != nombre_original:
            cambios.append(f"nombre: '{nombre_original}' → '{cliente_actualizado.nombre}'")
        
        descripcion = f"Se actualizó el cliente: {cliente_actualizado.nombre}"
        if cambios:
            descripcion += f". Cambios: {', '.join(cambios)}"
        else:
            descripcion += ". Sin cambios detectados"
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="EDITAR",
            descripcion=descripcion,
            modulo="Clientes"
        )

    def perform_destroy(self, instance):
        """Eliminar cliente y registrar en bitácora"""
        nombre_cliente = instance.nombre
        
        instance.delete()
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="ELIMINAR CLIENTE",
            descripcion=f"Se eliminó el cliente: {nombre_cliente}",
            modulo="Clientes"
        )

class RegistroBitacoraViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RegistroBitacora.objects.select_related('usuario').order_by('-fecha_hora')
    serializer_class = RegistroBitacoraSerializer
    
    def get_queryset(self):
        """Optimizar consulta y limitar resultados"""
        queryset = super().get_queryset()
        
        # Limitar a los últimos 500 registros por defecto
        limit = int(self.request.query_params.get('limit', 500))
        queryset = queryset[:limit]
        
        return queryset
