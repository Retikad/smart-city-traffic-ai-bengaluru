import sqlite3

DB='bengaluru_traffic.db'
# columns to ensure: mapping table -> list of (column_name, sql_type)
REQUIRED={
    'raw_traffic': [
        ('crowd_density','REAL'),
        ('eta_seconds','REAL'),
        ('weather_main','TEXT'),
        ('weather_description','TEXT'),
        ('weather_temp','REAL'),
        ('weather_humidity','REAL'),
        ('weather_rain','REAL'),
    ],
    'processed_traffic': [
        ('crowd_density','REAL'),
        ('eta_seconds','REAL'),
        ('weather_main','TEXT'),
        ('weather_description','TEXT'),
        ('weather_temp','REAL'),
        ('weather_humidity','REAL'),
        ('weather_rain','REAL'),
    ]
}


def ensure_columns():
    conn=sqlite3.connect(DB)
    cur=conn.cursor()
    for table, cols in REQUIRED.items():
        cur.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cur.fetchall()}  # name is at index 1
        for col, typ in cols:
            if col in existing:
                print(f"{table}.{col} already exists")
            else:
                sql = f"ALTER TABLE {table} ADD COLUMN {col} {typ}"
                print(f"Adding column: {sql}")
                cur.execute(sql)
                conn.commit()
    conn.close()

if __name__=='__main__':
    ensure_columns()
    print('Done')
