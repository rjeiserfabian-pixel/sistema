import os
import sys
import django

sys.path.append(r'C:\Users\JEISER\Desktop\PREMIUN\Sistemas-de-ventas')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raiz.settings')
django.setup()

from django.db import connection
from software.models.RepuestoModel import Repuesto

with connection.cursor() as cursor:
    table_name = Repuesto._meta.db_table
    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}'")
    columns = [row[0] for row in cursor.fetchall()]
    print(f"Columns in {table_name}:", columns)

