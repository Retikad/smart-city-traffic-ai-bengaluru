import sqlite3

def main():
    conn = sqlite3.connect('bengaluru_traffic.db')
    cur = conn.cursor()
    q = '''SELECT id, location_name, timestamp, current_speed, free_flow_speed, confidence, congestion_index
           FROM raw_traffic
           WHERE current_speed IS NULL OR free_flow_speed IS NULL OR confidence IS NULL OR congestion_index IS NULL OR timestamp IS NULL
           LIMIT 50'''
    cur.execute(q)
    rows = cur.fetchall()
    print('rows with nulls:', len(rows))
    for r in rows:
        print(r)
    conn.close()

if __name__ == '__main__':
    main()
