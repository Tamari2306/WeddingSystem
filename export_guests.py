import sqlite3
import csv

def export_guests_to_csv(csv_file_path):
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()

    cursor.execute('SELECT id, name, phone, qr_code_id, has_entered, qr_image_base64 FROM guests')
    guests = cursor.fetchall()

    with open(csv_file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        # Write header
        writer.writerow(['id', 'name', 'phone', 'qr_code_id', 'has_entered', 'qr_image_base64'])
        # Write data
        writer.writerows(guests)

    conn.close()
    print("✅ Guests exported successfully!")

# Usage
if __name__ == "__main__":
    export_guests_to_csv('exported_guests_with_qr.csv')
