import qrcode
import sqlite3
import os

DATABASE = 'guests.db'  # Path to your SQLite database
QR_FOLDER = 'static/qrcodes'  # Folder to store generated QR code images

# Create QR folder if it doesn't exist
if not os.path.exists(QR_FOLDER):
    os.makedirs(QR_FOLDER)

def get_db_connection():
    """Establishes connection to the database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def generate_qr_codes_script():
    """Generates QR codes for each guest and saves them in the database."""
    conn = get_db_connection()

    # Fetch the guests data from the database
    guests = conn.execute('SELECT id, name, phone, qr_code_id FROM guests').fetchall()

    for guest in guests:
        qr_code_id = guest['qr_code_id']
        guest_id = guest['id']

        if qr_code_id:  # Only generate if there's a QR code ID
            # Generate the QR code using the guest's qr_code_id
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_code_id)
            qr.make(fit=True)

            # Create the image of the QR code
            img = qr.make_image(fill_color="black", back_color="white")

            # Set the image file name
            img_filename = os.path.join(QR_FOLDER, f"{qr_code_id}.png")

            # Save the image to the disk
            try:
                img.save(img_filename)
                print(f"Saved QR code for {guest['name']} as {img_filename}")

                # Construct the URL for the saved QR code image
                qr_code_url = f"/static/qrcodes/{qr_code_id}.png"

                # Reconnect to the database and update the guest with the QR code URL
                conn_update = get_db_connection()
                conn_update.execute('UPDATE guests SET qr_code_url = ? WHERE id = ?', (qr_code_url, guest_id))
                conn_update.commit()  # Commit the changes to the database
                conn_update.close()
            except Exception as e:
                print(f"Error saving QR code for {guest['name']}: {e}")
        else:
            print(f"Skipping QR code generation for {guest['name']} (no QR code ID).")

    # Close the initial database connection
    conn.close()
    print("QR code generation process completed.")

if __name__ == '__main__':
    # Run the QR code generation function
    generate_qr_codes_script()