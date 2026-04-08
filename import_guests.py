import csv
import sqlite3
import os
import qrcode
import sys
import base64

# --- Get CSV filename dynamically ---
if len(sys.argv) > 1:
    csv_filename = sys.argv[1]
else:
    csv_filename = 'guests.csv'

if not os.path.exists(csv_filename):
    print(f"Error: File '{csv_filename}' does not exist!")
    sys.exit(1)

# --- Connect to database ---
conn = sqlite3.connect('guests.db')
cursor = conn.cursor()

# Create table if not exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS guests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    qr_code_id TEXT UNIQUE,
    qr_image_base64 TEXT,
    has_entered INTEGER DEFAULT 0,
    entry_time TEXT
)
''')

# Ensure qr_codes folder exists
os.makedirs('qr_codes', exist_ok=True)

# Find the highest GUEST-000X number already in DB
cursor.execute("SELECT qr_code_id FROM guests")
existing_qr_ids = cursor.fetchall()

existing_numbers = []
for qr_id in existing_qr_ids:
    if qr_id[0] and qr_id[0].startswith("GUEST-"):
        try:
            number = int(qr_id[0].replace("GUEST-", ""))
            existing_numbers.append(number)
        except ValueError:
            pass

next_guest_number = max(existing_numbers, default=0) + 1

# --- Read guests from CSV file ---
with open(csv_filename, 'r', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    
    if 'name' not in reader.fieldnames or 'phone' not in reader.fieldnames:
        print("Error: CSV must contain 'name' and 'phone' columns.")
        sys.exit(1)

    for row in reader:
        name = row['name'].strip()
        phone = row['phone'].strip()

        qr_code_id = f"GUEST-{next_guest_number:04d}"
        next_guest_number += 1

        try:
            # Generate QR Code
            qr = qrcode.make(qr_code_id)

            qr_filename = os.path.join('qr_codes', f'{qr_code_id}.png')
            qr.save(qr_filename)

            # Encode QR Code to base64
            with open(qr_filename, "rb") as image_file:
                qr_base64 = base64.b64encode(image_file.read()).decode('utf-8')

            # Insert into database
            cursor.execute('''
                INSERT INTO guests (name, phone, qr_code_id, qr_image_base64)
                VALUES (?, ?, ?, ?)
            ''', (name, phone, qr_code_id, qr_base64))

            print(f"✅ Added {name} (QR: {qr_code_id})")

        except sqlite3.IntegrityError:
            print(f"⚠️ Skipped {name} (duplicate entry)")

# Commit and close
conn.commit()
conn.close()

print("\n✅ Import complete!")
