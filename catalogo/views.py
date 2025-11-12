from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from catalogo.serializers.serializers_catalogo import CatalogoSerializer, MarcaSerializer, CategoriaSerializer
from .models import Catalogo, Marca, Categoria, Producto
from catalogo.serializers.serializers_producto import ProductoSerializer
from administracion.core.utils import registrar_bitacora
import requests
from django.conf import settings
from rest_framework import viewsets, filters

# Create your views here.

class CategoriaViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar Categorías.
    Permite filtrar por nombre: /api/categorias/?nombre=Computadoras
    """
    queryset = Categoria.objects.all().order_by('nombre')
    serializer_class = CategoriaSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="CREAR CATEGORIA",
            descripcion=f"Se creó la categoría: '{instance.nombre}'",
            modulo="Catalogo"
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="EDITAR CATEGORIA",
            descripcion=f"Se actualizó la categoría: '{instance.nombre}'",
            modulo="Catalogo"
        )

    def perform_destroy(self, instance):
        nombre_categoria = instance.nombre
        instance.delete()
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="ELIMINAR CATEGORIA",
            descripcion=f"Se eliminó la categoría: '{nombre_categoria}'",
            modulo="Catalogo"
        )


class MarcaViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar Marcas.
    Permite filtrar por nombre: /api/marcas/?nombre=HP
    """
    queryset = Marca.objects.all().order_by('nombre')
    serializer_class = MarcaSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="CREAR MARCA",
            descripcion=f"Se creó la marca: '{instance.nombre}'",
            modulo="Catalogo"
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="EDITAR MARCA",
            descripcion=f"Se actualizó la marca: '{instance.nombre}'",
            modulo="Catalogo"
        )

    def perform_destroy(self, instance):
        nombre_marca = instance.nombre
        instance.delete()
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="ELIMINAR MARCA",
            descripcion=f"Se eliminó la marca: '{nombre_marca}'",
            modulo="Catalogo"
        )


class CatalogoViewSet(viewsets.ModelViewSet):
    """
    API endpoint principal para gestionar el Catálogo (Productos).
    Incluye subida de imágenes a ImgBB y registro en Bitácora.
    """
    queryset = Catalogo.objects.all().order_by('-fecha_creacion')
    serializer_class = CatalogoSerializer

    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'marca__nombre', 'categoria__nombre', 'sku', 'descripcion']

    # --- LÓGICA DE IMG BB (adaptada de VehiculoViewSet) ---

    def create(self, request, *args, **kwargs):
        """
        Sobrescribe el método CREATE para manejar la subida de imagen ANTES de crear.
        """
        # 1. Pasa la request al manejador de imagen
        # 2. El manejador llama a 'super().create' (la acción original)
        return self.handle_image_upload(request, super().create)

    def update(self, request, *args, **kwargs):
        """
        Sobrescribe el método UPDATE para manejar la subida de imagen ANTES de actualizar.
        """
        # 1. Pasa la request al manejador de imagen
        # 2. El manejador llama a 'super().update' (la acción original)
        return self.handle_image_upload(request, super().update, *args, **kwargs)

    def handle_image_upload(self, request, action, *args, **kwargs):
        """
        Manejador que revisa, sube y reemplaza el archivo de imagen por una URL.
        """
        # IMPORTANTE: Usamos 'imagen_url' porque así se llama
        # el campo en tu CatalogoSerializer.
        imagen_file = request.FILES.get("imagen_url")

        if imagen_file:
            # 1. SI HAY ARCHIVO: Subir a ImgBB
            url = "https://api.imgbb.com/1/upload"
            payload = {"key": settings.API_KEY_IMGBB}
            files = {"image": imagen_file.read()}
            response = requests.post(url, payload, files=files)

            if response.status_code == 200:
                # 2. ÉXITO: Reemplazar el archivo por la URL en la request
                image_url = response.json()["data"]["url"]
                data = request.data.copy()
                data["imagen_url"] = image_url  # Reemplaza el archivo por la URL
                request._full_data = data  # Sobrescribe la data de la request
            else:
                # 3. FALLO: Devolver error
                return Response(
                    {"error": "Error al subir imagen a ImgBB", "details": response.text}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            # 4. SI NO HAY ARCHIVO (en un UPDATE):
            # Prevenir que la URL se borre si no se envía una nueva imagen
            if request.method in ["PUT", "PATCH"]:
                instance = self.get_object()
                data = request.data.copy()
                # Si 'imagen_url' no se envió en el formulario,
                # reasignamos la URL que ya existía en la base de datos.
                if not data.get("imagen_url"):
                    data["imagen_url"] = instance.imagen_url
                    request._full_data = data

        # 5. Ejecutar la acción original (super().create o super().update)
        # DRF se encargará de llamar a perform_create o perform_update DESPUÉS de esto.
        return action(request, *args, **kwargs)

    # --- LÓGICA DE BITÁCORA (Tus métodos originales, sin cambios) ---

    def perform_create(self, serializer):
        instance = serializer.save()
        
        # Obtenemos nombres para la bitácora
        marca_nombre = instance.marca.nombre if instance.marca else 'N/A'
        cat_nombre = instance.categoria.nombre if instance.categoria else 'N/A'
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="CREAR PRODUCTO",
            descripcion=f"Se creó el producto: '{instance.nombre}' (SKU: {instance.sku}, Marca: {marca_nombre}, Cat: {cat_nombre})",
            modulo="Catalogo"
        )

    def perform_update(self, serializer):
        # 1. Guardar estado original
        instance = self.get_object()
        nombre_orig = instance.nombre
        precio_orig = instance.precio
        marca_orig = instance.marca.nombre if instance.marca else 'N/A'
        cat_orig = instance.categoria.nombre if instance.categoria else 'N/A'
        
        # 2. Guardar cambios
        instance = serializer.save()

        # 3. Obtener nuevos valores
        marca_nueva = instance.marca.nombre if instance.marca else 'N/A'
        cat_nueva = instance.categoria.nombre if instance.categoria else 'N/A'

        # 4. Construir descripción de cambios
        cambios = []
        if instance.nombre != nombre_orig:
            cambios.append(f"nombre: '{nombre_orig}' → '{instance.nombre}'")
        if instance.precio != precio_orig:
            cambios.append(f"precio: '{precio_orig}' → '{instance.precio}'")
        if marca_orig != marca_nueva:
            cambios.append(f"marca: '{marca_orig}' → '{marca_nueva}'")
        if cat_orig != cat_nueva:
            cambios.append(f"categoría: '{cat_orig}' → '{cat_nueva}'")
        
        descripcion = f"Producto '{instance.nombre}' (SKU: {instance.sku}) actualizado"
        if cambios:
            descripcion += f". Cambios: {', '.join(cambios)}"
        else:
            descripcion += ". Sin cambios detectados en campos principales"

        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="EDITAR PRODUCTO",
            descripcion=descripcion,
            modulo="Catalogo"
        )

    def perform_destroy(self, instance):
        nombre_producto = instance.nombre
        sku_producto = instance.sku
        instance.delete()
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="ELIMINAR PRODUCTO",
            descripcion=f"Se eliminó el producto: '{nombre_producto}' (SKU: {sku_producto})",
            modulo="Catalogo"
        )

class ProductoViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar el Inventario Físico (Producto).
    """
    queryset = Producto.objects.all().order_by('-fecha_ingreso')
    serializer_class = ProductoSerializer
    # (Aquí puedes añadir filtros para 'catalogo_id' si lo necesitas)
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['catalogo']

    def perform_create(self, serializer):
        """Guardar item de inventario y registrar en bitácora"""
        
        # --- CORREGIDO ---
        # Simplemente llamamos a save(). El serializador ya sabe qué hacer
        # con 'catalogo_id' gracias al 'source'.
        instance = serializer.save() 
        
        # Obtenemos info para la bitácora
        # --- CORREGIDO --- (usamos 'catalogo' en minúscula)
        catalogo_nombre = instance.catalogo.nombre if instance.catalogo else 'N/A'
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="CREAR INVENTARIO (ITEM)",
            descripcion=f"Se añadió el item S/N: '{instance.numero_serie}' al producto: '{catalogo_nombre}' (Costo: {instance.costo})",
            modulo="Inventario" 
        )

    def perform_update(self, serializer):
        """Actualizar item de inventario y registrar en bitácora"""
        instance_orig = self.get_object()
        costo_orig = instance_orig.costo
        estado_orig = instance_orig.estado
        
        instance = serializer.save()

        cambios = []
        if instance.costo != costo_orig:
            cambios.append(f"costo: '{costo_orig}' → '{instance.costo}'")
        if instance.estado != estado_orig:
            cambios.append(f"estado: '{estado_orig}' → '{instance.estado}'")
        
        # --- CORREGIDO --- (confirmamos 'catalogo' en minúscula)
        descripcion = f"Item S/N: '{instance.numero_serie}' (del Catálogo: '{instance.catalogo.nombre}') actualizado"
        
        if cambios:
            descripcion += f". Cambios: {', '.join(cambios)}"
        else:
            descripcion += ". Sin cambios detectados."

        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="EDITAR INVENTARIO (ITEM)",
            descripcion=descripcion,
            modulo="Inventario"
        )

    def perform_destroy(self, instance):
        """Eliminar item de inventario y registrar en bitácora"""
        numero_serie_borrado = instance.numero_serie
        
        # --- CORREGIDO --- (confirmamos 'catalogo' en minúscula)
        catalogo_nombre = instance.catalogo.nombre if instance.catalogo else 'N/A'
        
        instance.delete()
        
        registrar_bitacora(
            request=self.request,
            usuario=self.request.user,
            accion="ELIMINAR INVENTARIO (ITEM)",
            descripcion=f"Se eliminó el item S/N: '{numero_serie_borrado}' (del Catálogo: '{catalogo_nombre}')",
            modulo="Inventario"
        )
