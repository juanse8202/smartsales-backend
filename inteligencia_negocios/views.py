from rest_framework.views import APIView
from rest_framework.response import Response
from .parser import ReportParser
from .generator import ReportGenerator

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

# Create your views here.

# Create your views here.
