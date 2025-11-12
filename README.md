# SMARTSALES365
## clonar repositorio
git clone [repository url]

## entorno virtual

### crear entorno virtual
python -m venv env
### activar En Windows
.\env\Scripts\activate
### activar En macOS/Linux
source env/bin/activate

## instalar dependencias
pip install -r requirements.txt

## Configura el proyecto:
Crea un archivo .env en la raíz del proyecto y rellénalo siguiendo el archivo .env.example.

## generar SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

## migraciones para la base de datos
python manage.py migrate

Nota: si hay conflictos con las migraciones ejecutar: 
python manage.py makemigrations --merge

presionar 'y' si sale el siguiente mensaje:
Conflicts detected; would you like to merge these migrations [y/n]?

## inicar servidor
python manage.py runserver


# SUBIR PORYECTO A GITHUD

paso previo: pip freeze > requirements.txt

git add .

git commit -m "mensaje descriptivo del cambio"

git pull origin main

## si hay conflictos

Nota: Resuelve los conflictos manualmente (usa tu editor o GitHub Desktop, VS Code, etc.).

Una vez resueltos, ejecuta:

opcional: git add .

git commit -m "Conflictos resueltos"

git push origin main

## si no hay conflictos

git push origin main