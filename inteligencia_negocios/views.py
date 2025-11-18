from rest_framework.views import APIView
from rest_framework.response import Response
from .parser import ReportParser
from .generator import ReportGenerator
from rest_framework.permissions import IsAuthenticated
from datetime import datetime

class GenerateReportView(APIView):
    def post(self, request):
        prompt = request.data.get('prompt', '').lower()
        
        # 1. Interpretar el prompt
        parser = ReportParser()
        parsed_request = parser.parse(prompt)
        # Ej: parsed_request = {'type': 'ventas', 'filters': {'date__gte': '2024-10-01'}, 'format': 'pdf'}

        # 2. Generar el reporte
        generator = ReportGenerator()
        return generator.generate(parsed_request)

class StandardReportView(APIView):
    """
    Genera reportes predefinidos y estándar sin necesidad de un prompt.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, report_key):
        
        # 1. PREPARAMOS EL PLAN (El dict que el Parser solía crear)
        parsed_request = {}
        today = datetime.now()

        # 2. DECIDIMOS QUÉ REPORTE HACER BASADO EN LA URL
        if report_key == 'sales_this_month_excel':
            parsed_request = {
                'type': 'ventas',
                'filters': {
                    'fecha__month': today.month,
                    'fecha__year': today.year
                },
                'format': 'excel',
                'group_by': None,
                'select_fields': ['id', 'fecha', 'cliente__nombre', 'total', 'estado']
            }
        
        elif report_key == 'inventory_available_pdf':
            parsed_request = {
                'type': 'inventario',
                'filters': {'estado': 'disponible'},
                'format': 'pdf',
                'group_by': 'categoria', # Agrupado por categoría
                'select_fields': []
            }
        
        else:
            return Response({'error': 'Reporte no válido.'}, status=404)

        # 3. LLAMAMOS AL MISMO GENERADOR
        # Reutilizamos 100% de nuestra lógica de PDF/Excel
        generator = ReportGenerator()
        return generator.generate(parsed_request)

# Create your views here.

# Create your views here.
