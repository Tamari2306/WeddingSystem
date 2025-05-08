import sqlite3

# Create (or connect to) the database
conn = sqlite3.connect('guests.db')

# Create a cursor to run SQL commands
cursor = conn.cursor()

# Create a table for guest information
cursor.execute('''
CREATE TABLE IF NOT EXISTS guests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    qr_code_id TEXT UNIQUE,
    has_entered TEXT DEFAULT 'No'
)
''')

# Save changes and close
conn.commit()
conn.close()

print("Guest database created successfully!")
