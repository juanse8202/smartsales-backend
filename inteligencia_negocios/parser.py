# reports/services/parser.py
from catalogo.models import Marca, Categoria

class ReportParser:
    
    # --- Cargamos las listas de palabras clave desde la BD ---
    try:
        MARCAS_CONOCIDAS = [m.nombre.lower() for m in Marca.objects.all()]
    except Exception:
        MARCAS_CONOCIDAS = ['lg', 'samsung', 'mabe', 'oster', 'mueller', 'etc']

    try:
        CATEGORIAS_MAPA = {
            'línea blanca': 'línea blanca',
            'blanca': 'línea blanca',
            'informática': 'línea gris (informática)',
            'gris': 'línea gris (informática)',
            'audio': 'línea marrón (audio/video)',
            'video': 'línea marrón (audio/video)',
            'marrón': 'línea marrón (audio/video)',
            'pae': 'pequeños electrodomésticos (pae)',
            'pequeños electrodomésticos': 'pequeños electrodomésticos (pae)'
        }
    except Exception:
        CATEGORIAS_MAPA = {}
        
    CAMPOS_MAPA = {
        'numero de serie': 'numero_serie',
        'costo': 'costo',
        'estado': 'estado',
        'precio': 'catalogo__precio',
        'nombre': 'catalogo__nombre',
        'garantía': 'garantia_vigente', # ¡Usamos la @property!
        'fin de garantia': 'fecha_fin_garantia', # ¡Usamos la @property!
        'nombre': 'catalogo__nombre'
    }


    def parse(self, prompt):
        result = {
            'type': 'inventario', # Asumimos que es de inventario
            'filters': {},
            'format': 'json',
            'group_by': None,
            'select_fields': [] # <--- NUEVA CLAVE
        }

        # --- A. VERIFICAR TIPO DE REPORTE ---
        # Si no pide inventario, producto o stock, no sabemos qué hacer
        if not any(word in prompt for word in ['inventario', 'producto', 'stock', 'reporte']):
            raise ValueError("No entiendo el reporte. Prueba pidiendo 'reporte de inventario'.")

        # --- B. DETECTAR FORMATO ---
        if 'pdf' in prompt:
            result['format'] = 'pdf'
        elif 'excel' in prompt:
            result['format'] = 'excel'

        # --- C. DETECTAR AGRUPACIÓN (GROUP BY) ---
        if 'por categoria' in prompt or 'agrupado por categoria' in prompt:
            result['group_by'] = 'categoria'
        elif 'por marca' in prompt or 'agrupado por marca' in prompt:
            result['group_by'] = 'marca'

        # --- D. DETECTAR FILTROS ---
        if 'disponible' in prompt:
            result['filters']['estado'] = 'disponible'
        elif 'vendido' in prompt:
            result['filters']['estado'] = 'vendido'
        
        # 1. Detectar marca como filtro
        for marca in self.MARCAS_CONOCIDAS:
            if marca in prompt:
                result['filters']['catalogo__marca__nombre__icontains'] = marca
                break 

        # 2. Detectar categoría como filtro
        for keyword, nombre_categoria in self.CATEGORIAS_MAPA.items():
            if keyword in prompt:
                result['filters']['catalogo__categoria__nombre__icontains'] = nombre_categoria
                break
        
        if not result['group_by']:
            for keyword, field_name in self.CAMPOS_MAPA.items():
                if keyword in prompt:
                    result['select_fields'].append(field_name)
            
            # Si no seleccionó campos, usaremos una lista por defecto
            if not result['select_fields']:
                result['select_fields'] = ['numero_serie', 'catalogo__nombre', 'estado']

        return result