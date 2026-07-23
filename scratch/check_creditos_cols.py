import psycopg2

try:
    conn = psycopg2.connect(
        dbname="facsiswave",
        user="postgres",
        password="root",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    
    print("--- COLUMNS for creditos ---")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'creditos'")
    for row in cur.fetchall():
        print(row[0])
        
    cur.close()
    conn.close()
except Exception as e:
    print(e)
