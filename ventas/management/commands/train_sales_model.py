# inteligencia_negocios/management/commands/train_sales_model.py

import pandas as pd
import joblib
from django.core.management.base import BaseCommand
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from sklearn.ensemble import RandomForestRegressor

# Importa tus modelos de ventas
from ventas.models import Venta

# Define dónde se guardará el modelo entrenado
MODEL_FILE_PATH = 'sales_model.pkl'

class Command(BaseCommand):
    help = 'Entrena el modelo de predicción de ventas (RandomForestRegressor) y lo guarda.'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando entrenamiento del modelo de predicción...")

        # 1. OBTENER DATOS HISTÓRICOS
        # Obtenemos solo ventas completadas 
        sales_data = Venta.objects.filter(estado='completada') \
            .annotate(month=TruncMonth('fecha')) \
            .values('month') \
            .annotate(total_ventas=Sum('total')) \
            .order_by('month')

        if not sales_data:
            self.stderr.write("No hay datos de ventas completadas para entrenar.")
            return

        # 2. PREPARAR DATOS (Feature Engineering)
        # Convertimos los datos al formato que scikit-learn entiende
        df = pd.DataFrame(list(sales_data))
        
        # Convertimos la columna 'month' (que es una fecha) en features numéricos
        df['year'] = df['month'].dt.year
        df['month_num'] = df['month'].dt.month
        
        # 'X' son las características (Año, Mes)
        X = df[['year', 'month_num']]
        # 'y' es lo que queremos predecir (Total de Ventas)
        y = df['total_ventas']

        # 3. ENTRENAR EL MODELO 
        # (Usamos 100 árboles, puedes ajustar esto)
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)

        # 4. GUARDAR (SERIALIZAR) EL MODELO [cite: 226, 247]
        # Usamos joblib para guardar el modelo entrenado en un archivo
        joblib.dump(model, MODEL_FILE_PATH)

        self.stdout.write(self.style.SUCCESS(f"¡Modelo entrenado y guardado exitosamente en {MODEL_FILE_PATH}!"))