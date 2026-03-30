import sqlite3, time
conn = sqlite3.connect('bengaluru_traffic.db')
cur = conn.cursor()
cur.execute('select count(*) from raw_traffic')
before = cur.fetchone()[0]
print('before', before)
conn.close()

time.sleep(70)
conn = sqlite3.connect('bengaluru_traffic.db')
cur = conn.cursor()
cur.execute('select count(*) from raw_traffic')
after = cur.fetchone()[0]
print('after', after)
print('added', after-before)
conn.close()
