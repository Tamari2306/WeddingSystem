import sqlite3

def add_guest(name, phone, qr_code_id):
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO guests (name, phone, qr_code_id)
            VALUES (?, ?, ?)
        ''', (name, phone, qr_code_id))
        conn.commit()
        print(f"Guest '{name}' added successfully!")
    except sqlite3.IntegrityError:
        print(f"Guest with QR Code ID '{qr_code_id}' already exists.")
    finally:
        conn.close()

# Example guest
add_guest("John Doe", "+123456789", "QR123456")
