import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "bengaluru_traffic.db")
print("DB Path:", DB_PATH)
if not os.path.exists(DB_PATH):
    print("Database file not found, nothing to migrate.")
    exit(0)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(raw_traffic)")
cols = [row[1] for row in cur.fetchall()]
print("Existing columns:", cols)

adds = []
if 'eta_seconds' not in cols:
    adds.append(('eta_seconds', 'REAL'))
if 'weather_main' not in cols:
    adds.append(('weather_main', 'TEXT'))
if 'weather_description' not in cols:
    adds.append(('weather_description', 'TEXT'))
if 'weather_temp' not in cols:
    adds.append(('weather_temp', 'REAL'))
if 'weather_humidity' not in cols:
    adds.append(('weather_humidity', 'REAL'))
if 'weather_rain' not in cols:
    adds.append(('weather_rain', 'REAL'))

if not adds:
    print('No columns to add.')
else:
    for name, typ in adds:
        sql = f"ALTER TABLE raw_traffic ADD COLUMN {name} {typ}"
        print('Executing:', sql)
        cur.execute(sql)
    conn.commit()
    print('Migration complete, added columns:', [a[0] for a in adds])

conn.close()
