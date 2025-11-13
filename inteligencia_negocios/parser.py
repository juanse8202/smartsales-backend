# reports/services/parser.py
from catalogo.models import Marca, Categoria
from datetime import datetime
from dateutil.relativedelta import relativedelta

class ReportParser:
    
    # --- (Palabras clave de Marcas, Categorías y Campos se quedan igual) ---
    try:
        MARCAS_CONOCIDAS = [m.nombre.lower() for m in Marca.objects.all()]
    except Exception:
        MARCAS_CONOCIDAS = ['lg', 'samsung', 'mabe', 'oster', 'mueller', 'etc']

    try:
        CATEGORIAS_MAPA = {
            'línea blanca': 'línea blanca', 'blanca': 'línea blanca',
            'informática': 'línea gris (informática)', 'gris': 'línea gris (informática)',
            'audio': 'línea marrón (audio/video)', 'video': 'línea marrón (audio/video)',
            'marrón': 'línea marrón (audio/video)',
            'pae': 'pequeños electrodomésticos (pae)',
        }
    except Exception:
        CATEGORIAS_MAPA = {}
    
    CAMPOS_MAPA = {
        'numero de serie': 'numero_serie', 'costo': 'costo',
        'garantía': 'garantia_vigente', 'fin de garantia': 'fecha_fin_garantia',
        'nombre': 'catalogo__nombre', 'precio': 'catalogo__precio',
        'cliente': 'cliente__nombre', 'total': 'total', 'fecha': 'fecha',
        'estado': 'estado', 'subtotal': 'subtotal', 'descuento': 'descuento'
    }


    def parse(self, prompt):
        result = {
            'type': None,
            'filters': {},
            'format': 'json',
            'group_by': None,
            'select_fields': []
        }

        # --- A. DETECTAR TIPO DE REPORTE (¡ORDEN CORREGIDO!) ---
        # 1. Revisamos INVENTARIO primero, es más específico.
        if 'por producto' in prompt or 'por cliente' in prompt:
            result['type'] = 'ventas'
        
        # 2. Si no es un group_by de ventas, revisamos palabras clave de ventas.
        elif 'venta' in prompt or 'pedido' in prompt or 'ingreso' in prompt:
            result['type'] = 'ventas'
            
        # 3. Si no es ventas, revisamos palabras clave de inventario.
        elif 'inventario' in prompt or 'stock' in prompt or 'producto' in prompt:
            result['type'] = 'inventario'
        
        else:
            # Si el prompt era solo "reporte por marca", no sabemos qué reportar
            if result['group_by']:
                raise ValueError("No entiendo si pides reporte de 'ventas' o 'inventario' por marca/categoría.")
            else:
                raise ValueError("No entiendo si pides un reporte de 'ventas' o de 'inventario'.")

        # --- B. DETECTAR FORMATO ---
        if 'pdf' in prompt: result['format'] = 'pdf'
        elif 'excel' in prompt: result['format'] = 'excel'

        # --- C. DETECTAR AGRUPACIÓN (¡LÓGICA CORREGIDA!) ---
        # La agrupación depende del tipo de reporte que ya detectamos
        
        if result['type'] == 'ventas':
            if 'por cliente' in prompt:
                result['group_by'] = 'cliente'
            elif 'por producto' in prompt: # "por producto" SÓLO aplica a ventas
                result['group_by'] = 'producto'
            elif 'por categoria' in prompt:
                result['group_by'] = 'categoria'
            elif 'por marca' in prompt:
                result['group_by'] = 'marca'
        
        elif result['type'] == 'inventario':
            # "por producto" o "por cliente" no tienen sentido aquí
            if 'por categoria' in prompt: 
                result['group_by'] = 'categoria'
            elif 'por marca' in prompt:
                result['group_by'] = 'marca'

        # --- D. DETECTAR FILTROS (Sin cambios, ya era correcto) ---
        
        # Filtros de Estado
        if 'disponible' in prompt and result['type'] == 'inventario':
            result['filters']['estado'] = 'disponible'
        elif 'vendido' in prompt and result['type'] == 'inventario':
            result['filters']['estado'] = 'vendido'
        elif 'pendiente' in prompt and result['type'] == 'ventas':
            result['filters']['estado'] = 'pendiente'
        elif 'completada' in prompt and result['type'] == 'ventas':
            result['filters']['estado'] = 'completada'
        
        # Filtros de Fecha
        if result['type'] == 'ventas':
            
            # 1. Decidimos el prefijo del filtro de fecha
            date_prefix = 'fecha__' # Por defecto (para Venta)
            if result['group_by'] in ['producto', 'categoria', 'marca']:
                # Si agrupamos así, el Generator consulta DetalleVenta
                date_prefix = 'venta__fecha__' 

            # 2. Aplicamos los filtros de fecha con el prefijo correcto
            today = datetime.now()
            if 'hoy' in prompt:
                result['filters'][f'{date_prefix}date'] = today.date()
            elif 'este mes' in prompt:
                result['filters'][f'{date_prefix}month'] = today.month
                result['filters'][f'{date_prefix}year'] = today.year
            elif 'mes pasado' in prompt:
                last_month = today - relativedelta(months=1)
                result['filters'][f'{date_prefix}month'] = last_month.month
                result['filters'][f'{date_prefix}year'] = last_month.year
        
        # Filtros de Marca/Categoría
        filter_prefix = ''
        if result['type'] == 'inventario':
            # Consultas de inventario siempre empiezan en Producto
            filter_prefix = 'catalogo__'
        elif result['type'] == 'ventas':
            # Consultas agrupadas por producto/cat/marca empiezan en DetalleVenta
            if result['group_by'] in ['producto', 'categoria', 'marca']:
                filter_prefix = 'catalogo__'
            else:
                # Consultas agrupadas por cliente o listados simples empiezan en Venta
                filter_prefix = 'detalles__catalogo__'

        # 2. Aplicar los filtros con el prefijo correcto
        for marca in self.MARCAS_CONOCIDAS:
            if marca in prompt:
                # Usamos f-string para construir la clave del filtro
                result['filters'][f'{filter_prefix}marca__nombre__icontains'] = marca
                break 
        
        for keyword, nombre_categoria in self.CATEGORIAS_MAPA.items():
            if keyword in prompt:
                result['filters'][f'{filter_prefix}categoria__nombre__icontains'] = nombre_categoria
                break
        
        # --- E. DETECTAR CAMPOS SELECCIONADOS (Sin cambios, ya era correcto) ---
        if not result['group_by']:
            for keyword, field_name in self.CAMPOS_MAPA.items():
                if keyword in prompt:
                    result['select_fields'].append(field_name)
            
            if not result['select_fields']:
                if result['type'] == 'inventario':
                    result['select_fields'] = ['numero_serie', 'catalogo__nombre', 'estado']
                elif result['type'] == 'ventas':
                    result['select_fields'] = ['id', 'fecha', 'cliente__nombre', 'total', 'estado']

        return result