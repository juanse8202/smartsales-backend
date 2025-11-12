from django.urls import path, include
from rest_framework.routers import DefaultRouter
from catalogo.views import CategoriaViewSet, MarcaViewSet, CatalogoViewSet, ProductoViewSet

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet)
router.register(r'marcas', MarcaViewSet)
router.register(r'catalogo', CatalogoViewSet)
router.register(r'productos', ProductoViewSet)


urlpatterns = [
    path('', include(router.urls)),
]