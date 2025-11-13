# reports/services/generator.py
from django.http import HttpResponse
from django.db.models import Count, Sum # ¡IMPORTANTE: Añadir Sum!
from rest_framework.response import Response
import pandas as pd
import datetime

# --- IMPORTAMOS TODOS LOS MODELOS NECESARIOS ---
from catalogo.models import Producto, Catalogo, Marca, Categoria
from ventas.models import Venta, DetalleVenta # ¡NUEVO!

# --- IMPORTACIONES DE REPORTLAB ---
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

class ReportGenerator:
    def generate(self, parsed_request):
        
        formato = parsed_request['format']
        data = []
        report_title = "Reporte" # Título genérico

        # --- CASO 1: REPORTE DE INVENTARIO (Sin cambios) ---
        if parsed_request['type'] == 'inventario':
            report_title = "Reporte de Inventario"
            queryset = Producto.objects.filter(**parsed_request['filters'])
            group_by = parsed_request.get('group_by')
            
            if group_by:
                if group_by == 'categoria':
                    report_title = "Inventario por Categoría"
                    data = list(queryset.values('catalogo__categoria__nombre').annotate(total_items=Count('id')).order_by('-total_items'))
                elif group_by == 'marca':
                    report_title = "Inventario por Marca"
                    data = list(queryset.values('catalogo__marca__nombre').annotate(total_items=Count('id')).order_by('-total_items'))
            else:
                fields_to_select = parsed_request.get('select_fields')
                for producto in queryset:
                    row = {}
                    for field_name in fields_to_select:
                        if field_name == 'catalogo__nombre': row['nombre'] = producto.catalogo.nombre
                        elif field_name == 'catalogo__precio': row['precio'] = producto.catalogo.precio
                        else: row[field_name] = getattr(producto, field_name, None)
                    data.append(row)

        # --- CASO 2: REPORTE DE VENTAS (¡NUEVO BLOQUE!) ---
        elif parsed_request['type'] == 'ventas':
            report_title = "Reporte de Ventas"
            group_by = parsed_request.get('group_by')
            filters = parsed_request['filters']
            
            if group_by == 'cliente':
                report_title = "Reporte de Ventas por Cliente"
                queryset = Venta.objects.filter(**filters)
                data = list(
                    # --- CORRECCIÓN ---
                    # Agrupamos por nombre y nit_ci (o razon_social si prefieres)
                    queryset.values('cliente__nombre', 'cliente__nit_ci') 
                    .annotate(
                        cantidad_compras=Count('id'),
                        monto_total=Sum('total')
                    )
                    .order_by('-monto_total')
                )

            elif group_by == 'producto':
                report_title = "Reporte de Ventas por Producto"
                # [cite_start]"agrupado por producto" [cite: 54]
                queryset = DetalleVenta.objects.filter(**filters)
                data = list(
                    queryset.values('catalogo__nombre') # Agrupamos por nombre de catálogo
                    .annotate(
                        cantidad_unidades=Sum('cantidad'),
                        monto_total=Sum('total')
                    )
                    .order_by('-monto_total')
                )
            
            elif group_by == 'categoria':
                report_title = "Reporte de Ventas por Categoría"
                queryset = DetalleVenta.objects.filter(**filters)
                data = list(
                    queryset.values('catalogo__categoria__nombre')
                    .annotate(
                        cantidad_unidades=Sum('cantidad'),
                        monto_total=Sum('total')
                    )
                    .order_by('-monto_total')
                )

            elif group_by == 'marca':
                report_title = "Reporte de Ventas por Marca"
                queryset = DetalleVenta.objects.filter(**filters)
                data = list(
                    queryset.values('catalogo__marca__nombre')
                    .annotate(
                        cantidad_unidades=Sum('cantidad'),
                        monto_total=Sum('total')
                    )
                    .order_by('-monto_total')
                )

            else:
                # Listado simple de ventas
                report_title = "Listado de Ventas"
                fields_to_select = parsed_request.get('select_fields')
                # (Usamos .values() para campos de Venta)
                queryset = Venta.objects.filter(**filters)
                data = list(queryset.values(*fields_to_select))

        else:
             return Response({'error': 'Tipo de reporte no válido.'}, status=400)

        # --- VALIDACIÓN (Si no hay datos) ---
        if not data:
            return Response({'error': 'No hay datos para este reporte'}, status=404)

        # --- RENDERIZAR EL FORMATO SOLICITADO ---
        if formato == 'json':
            return Response({'report_data': data})

        elif formato == 'excel':
            df = pd.DataFrame(data)
            
            # Limpieza de Timezones (para todas las columnas de fecha)
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].dt.tz_localize(None)
            
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="reporte_{parsed_request["type"]}.xlsx"'
            
            df.to_excel(response, index=False)
            return response # <-- Corregido (solo un return)

        elif formato == 'pdf':
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="reporte_{parsed_request["type"]}.pdf"'
            doc = SimpleDocTemplate(response, pagesize=landscape(A4))
            
            flowables = []
            styles = getSampleStyleSheet()
            title = Paragraph(report_title, styles['h1'])
            flowables.append(title)
            
            # Convertir datos a lista de listas
            headers = list(data[0].keys())
            table_data = [headers]
            for row_dict in data:
                row_list = []
                for header in headers:
                    value = row_dict.get(header)
                    if isinstance(value, (datetime.datetime, datetime.date)):
                         value = value.strftime('%Y-%m-%d')
                    elif isinstance(value, (int, float)):
                        value = str(value) # Convertir números a string
                    elif value is None:
                        value = "N/A"
                    value = str(value) # Fallback final
                    row_list.append(value)
                table_data.append(row_list)

            # Crear y estilizar tabla
            pdf_table = Table(table_data)
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ])
            pdf_table.setStyle(style)
            flowables.append(pdf_table)

            doc.build(flowables)
            return response

        return Response({'error': 'Formato no soportado.'}, status=400)