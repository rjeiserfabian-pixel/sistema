import sqlite3
import os

db_path = 'db.sqlite3'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- TABLES ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for t in tables:
        print(t[0])
        
    print("\n--- SCHEMA FOR cuotasventa ---")
    try:
        cursor.execute("PRAGMA table_info(cuotasventa)")
        columns = cursor.fetchall()
        for col in columns:
            print(col)
    except Exception as e:
        print(e)
        
    conn.close()
else:
    print("Database not found")
