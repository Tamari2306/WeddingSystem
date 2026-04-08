import sqlite3

conn = sqlite3.connect('guests.db')
cursor = conn.cursor()
cursor.execute('UPDATE guests SET has_entered = 0')
conn.commit()
conn.close()

print("All guest statuses reset to NOT entered.")
