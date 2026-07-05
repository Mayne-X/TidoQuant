import sqlite3

conn = sqlite3.connect('journal/tidoquant.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT response FROM agent_logs WHERE trade_id=4 AND agent_name="manager"')
row = cur.fetchone()
if row:
    print(row['response'])
else:
    print("No log found")
