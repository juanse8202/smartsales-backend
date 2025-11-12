# reports/services/generator.py
from django.http import HttpResponse
from django.db.models import Count
from rest_framework.response import Response
from catalogo.models import Producto, Catalogo, Marca, Categoria # Importamos modelos
import pandas as pd

class ReportGenerator:
    def generate(self, parsed_request):
        
        formato = parsed_request['format']
        data = []

        # --- REPORTE DE INVENTARIO ---
        if parsed_request['type'] == 'inventario':
            
            queryset = Producto.objects.filter(**parsed_request['filters'])
            group_by = parsed_request.get('group_by')
            
            if group_by:
                # --- SI SE AGRUPA (Como antes) ---
                # Si se agrupa, ignoramos la selección de campos.
                if group_by == 'categoria':
                    data = list(queryset.values('catalogo__categoria__nombre').annotate(total_items=Count('id')).order_by('-total_items'))
                elif group_by == 'marca':
                    data = list(queryset.values('catalogo__marca__nombre').annotate(total_items=Count('id')).order_by('-total_items'))
            
            else:
                # --- SI NO SE AGRUPA (Lógica Nueva) ---
                # Usamos los campos que el Parser detectó
                fields_to_select = parsed_request.get('select_fields')
                
                # Iteramos sobre el queryset (¡esto es más lento que .values()!)
                for producto in queryset:
                    row = {}
                    for field_name in fields_to_select:
                        # Usamos 'getattr' para acceder a campos (ej. 'estado')
                        # y también a propiedades (ej. 'garantia_vigente')
                        if field_name == 'catalogo__nombre':
                            row['nombre'] = producto.catalogo.nombre
                        elif field_name == 'catalogo__precio':
                            row['precio'] = producto.catalogo.precio # <-- Lo añadimos
                        else:
                            # Esto funciona para 'numero_serie', 'costo'
                            # y tus @property como 'garantia_vigente'
                            row[field_name] = getattr(producto, field_name, None)
                    data.append(row)

        # --- RENDERIZAR EL FORMATO SOLICITADO ---
        if formato == 'json':
            return Response({'report_data': data})

        elif formato == 'excel':
            if not data:
                return Response({'error': 'No hay datos para este reporte'}, status=404)
            df = pd.DataFrame(data)
            if 'fecha_ingreso' in df.columns:
                df['fecha_ingreso'] = pd.to_datetime(df['fecha_ingreso']).dt.tz_localize(None)
            
            # Si 'fecha_venta' está en el reporte...
            if 'fecha_venta' in df.columns:
                df['fecha_venta'] = pd.to_datetime(df['fecha_venta']).dt.tz_localize(None)

            # (Si añades reportes de ventas, también necesitarás esto para 'fecha')
            if 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha']).dt.tz_localize(None)
            
            # 3. Crear la respuesta HTTP
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename="reporte_inventario.xlsx"'
            
            # 4. Escribir el DataFrame (ahora limpio) en el archivo Excel
            df.to_excel(response, index=False)
            return response
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename="reporte_inventario.xlsx"'
            df.to_excel(response, index=False)
            return response

        elif formato == 'pdf':
            # (Tu lógica de PDF aquí)
            pass

        return Response({'error': 'Formato no soportado.'}, status=400)