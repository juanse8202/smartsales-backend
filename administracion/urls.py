from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (LogoutView, CustomTokenObtainPairView, RegisterView, ProfileView, ChangePasswordView, MiClienteView, CambiarContrasenaView)
from .views import UserViewSet, RoleViewSet, PermissionViewSet, ClienteViewSet, CiudadViewSet, DepartamentoViewSet, RegistroBitacoraViewSet
from rest_framework_simplejwt.views import (TokenRefreshView, )


router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'permissions', PermissionViewSet)
router.register(r'clientes', ClienteViewSet)
router.register(r'ciudades', CiudadViewSet)
router.register(r'departamentos', DepartamentoViewSet)
router.register(r'bitacoras', RegistroBitacoraViewSet)

urlpatterns = [
    path('administracion/', include(router.urls)),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('administracion/mi-cliente/', MiClienteView.as_view(), name='mi_cliente'),
    path('administracion/cambiar-contrasena/', CambiarContrasenaView.as_view(), name='cambiar_contrasena'),
]
