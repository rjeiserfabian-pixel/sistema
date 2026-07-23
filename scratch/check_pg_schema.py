import psycopg2
import sys

try:
    conn = psycopg2.connect(
        dbname="facsiswave",
        user="postgres",
        password="root",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    
    print("--- TABLES ---")
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    for row in cur.fetchall():
        print(row[0])
        
    print("\n--- COLUMNS for cuotasventa ---")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'cuotasventa'")
    for row in cur.fetchall():
        print(row[0])
        
    cur.close()
    conn.close()
except Exception as e:
    print(e)
