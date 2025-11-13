# reports/services/parser.py
from catalogo.models import Marca, Categoria
from datetime import datetime
from dateutil.relativedelta import relativedelta

class ReportParser:
    
    # --- Palabras clave de Inventario (como antes) ---
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
    
    # --- Palabras clave de Campos (Ampliadas) ---
    CAMPOS_MAPA = {
        # Campos de Inventario
        'numero de serie': 'numero_serie', 'costo': 'costo',
        'garantía': 'garantia_vigente', 'fin de garantia': 'fecha_fin_garantia',
        'nombre': 'catalogo__nombre', 'precio': 'catalogo__precio',
        
        # Campos de Venta (Nuevos)
        'cliente': 'cliente__nombre', 'total': 'total', 'fecha': 'fecha',
        'estado': 'estado', 'subtotal': 'subtotal', 'descuento': 'descuento'
    }

    def parse(self, prompt):
        result = {
            'type': None, # Ya no asumimos 'inventario'
            'filters': {},
            'format': 'json',
            'group_by': None,
            'select_fields': []
        }

        # --- A. DETECTAR TIPO DE REPORTE (¡AMPLIADO!) ---
        if 'venta' in prompt or 'pedido' in prompt or 'ingreso' in prompt:
            result['type'] = 'ventas'
        elif 'inventario' in prompt or 'producto' in prompt or 'stock' in prompt:
            result['type'] = 'inventario'
        else:
            raise ValueError("No entiendo si pides un reporte de 'ventas' o de 'inventario'.")

        # --- B. DETECTAR FORMATO ---
        if 'pdf' in prompt: result['format'] = 'pdf'
        elif 'excel' in prompt: result['format'] = 'excel'

        # --- C. DETECTAR AGRUPACIÓN (¡AMPLIADO!) ---
        if 'por categoria' in prompt: result['group_by'] = 'categoria'
        elif 'por marca' in prompt: result['group_by'] = 'marca'
        elif 'por cliente' in prompt: result['group_by'] = 'cliente'
        elif 'por producto' in prompt: result['group_by'] = 'producto' # Para agrupar ventas por producto

        # --- D. DETECTAR FILTROS (¡AMPLIADO!) ---
        
        # Filtros de Estado (pueden aplicar a ambos)
        if 'disponible' in prompt and result['type'] == 'inventario':
            result['filters']['estado'] = 'disponible'
        elif 'vendido' in prompt and result['type'] == 'inventario':
            result['filters']['estado'] = 'vendido'
        elif 'pendiente' in prompt and result['type'] == 'ventas':
            result['filters']['estado'] = 'pendiente'
        elif 'completada' in prompt and result['type'] == 'ventas':
            result['filters']['estado'] = 'completada'
        
        # Filtros de Fecha (para Ventas)
        if result['type'] == 'ventas':
            today = datetime.now()
            if 'hoy' in prompt:
                result['filters']['fecha__date'] = today.date()
            elif 'este mes' in prompt:
                result['filters']['fecha__month'] = today.month
                result['filters']['fecha__year'] = today.year
            elif 'mes pasado' in prompt:
                last_month = today - relativedelta(months=1)
                result['filters']['fecha__month'] = last_month.month
                result['filters']['fecha__year'] = last_month.year
        
        # Filtros de Marca/Categoría (pueden aplicar a ambos)
        for marca in self.MARCAS_CONOCIDAS:
            if marca in prompt:
                filter_key = 'catalogo__marca__nombre__icontains' if result['type'] == 'inventario' else 'detalles__catalogo__marca__nombre__icontains'
                result['filters'][filter_key] = marca
                break 
        for keyword, nombre_categoria in self.CATEGORIAS_MAPA.items():
            if keyword in prompt:
                filter_key = 'catalogo__categoria__nombre__icontains' if result['type'] == 'inventario' else 'detalles__catalogo__categoria__nombre__icontains'
                result['filters'][filter_key] = nombre_categoria
                break
        
        # --- E. DETECTAR CAMPOS SELECCIONADOS ---
        if not result['group_by']:
            for keyword, field_name in self.CAMPOS_MAPA.items():
                if keyword in prompt:
                    result['select_fields'].append(field_name)
            
            # Asignar campos por defecto si no se seleccionó ninguno
            if not result['select_fields']:
                if result['type'] == 'inventario':
                    result['select_fields'] = ['numero_serie', 'catalogo__nombre', 'estado']
                elif result['type'] == 'ventas':
                    result['select_fields'] = ['id', 'fecha', 'cliente__nombre', 'total', 'estado']

        return result