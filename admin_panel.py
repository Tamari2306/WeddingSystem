import tkinter as tk
from tkinter import filedialog, messagebox
import csv
import sqlite3
import os
import qrcode
import zipfile
from datetime import datetime

# ---------- Helper Functions ----------

def import_guests_from_csv(csv_filename='guests.csv'):
    if not os.path.exists(csv_filename):
        messagebox.showerror("Error", f"File '{csv_filename}' does not exist!")
        return

    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS guests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        qr_code_id TEXT UNIQUE,
        has_entered INTEGER DEFAULT 0,
        entry_time TEXT
    )
    ''')

    os.makedirs('qr_codes', exist_ok=True)

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

    with open(csv_filename, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        
        if 'name' not in reader.fieldnames or 'phone' not in reader.fieldnames:
            messagebox.showerror("Error", "CSV must contain 'name' and 'phone' columns.")
            return

        for row in reader:
            name = row['name'].strip()
            phone = row['phone'].strip()

            qr_code_id = f"GUEST-{next_guest_number:04d}"
            next_guest_number += 1

            try:
                cursor.execute('''
                    INSERT INTO guests (name, phone, qr_code_id)
                    VALUES (?, ?, ?)
                ''', (name, phone, qr_code_id))

                qr = qrcode.make(qr_code_id)
                qr.save(os.path.join('qr_codes', f'{qr_code_id}.png'))

            except sqlite3.IntegrityError:
                pass  # Skip duplicates

    conn.commit()
    conn.close()
    messagebox.showinfo("Success", "Import complete!")

def export_guests_to_csv(csv_file_path='exported_guests.csv'):
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()

    cursor.execute('SELECT id, name, phone, qr_code_id, has_entered FROM guests')
    guests = cursor.fetchall()

    with open(csv_file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'name', 'phone', 'qr_code_id', 'has_entered'])
        writer.writerows(guests)

    conn.close()
    messagebox.showinfo("Success", f"Guests exported to '{csv_file_path}' successfully!")

def zip_qr_codes(output_zip_path='qr_codes.zip'):
    qr_folder = 'qr_codes'
    
    if not os.path.exists(qr_folder):
        messagebox.showerror("Error", f"Folder '{qr_folder}' does not exist!")
        return
    
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(qr_folder):
            for file in files:
                if file.endswith('.png'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, qr_folder)
                    zipf.write(file_path, arcname)
    
    messagebox.showinfo("Success", f"QR codes zipped successfully into '{output_zip_path}'!")

def view_all_guests():
    conn = sqlite3.connect('guests.db')
    cursor = conn.cursor()

    cursor.execute('SELECT id, name, phone, qr_code_id, has_entered, entry_time FROM guests')
    guests = cursor.fetchall()

    view_window = tk.Toplevel()
    view_window.title("Guest List")
    view_window.geometry("600x400")

    text = tk.Text(view_window)
    text.pack(expand=True, fill=tk.BOTH)

    for guest in guests:
        id, name, phone, qr_code_id, has_entered, entry_time = guest
        status = "✅ Entered" if has_entered else "🕑 Not Entered"
        text.insert(tk.END, f"[{id}] {name} | {phone} | {qr_code_id} | {status} | {entry_time or 'N/A'}\n")

    conn.close()

def on_import():
    csv_filename = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv")])
    if csv_filename:
        import_guests_from_csv(csv_filename)

def on_export():
    csv_filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
    if csv_filename:
        export_guests_to_csv(csv_filename)

def on_zip():
    zip_filename = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP Files", "*.zip")])
    if zip_filename:
        zip_qr_codes(zip_filename)

def on_view():
    view_all_guests()

# ---------- GUI Setup ----------
def setup_gui():
    root = tk.Tk()
    root.title("Wedding QR Code Admin Panel")
    root.geometry("400x300")

    label = tk.Label(root, text="🎯 Choose an option:", font=("Arial", 14))
    label.pack(pady=20)

    import_btn = tk.Button(root, text="Import Guests from CSV", width=25, command=on_import)
    import_btn.pack(pady=5)

    export_btn = tk.Button(root, text="Export Guests to CSV", width=25, command=on_export)
    export_btn.pack(pady=5)

    zip_btn = tk.Button(root, text="Zip All QR Codes", width=25, command=on_zip)
    zip_btn.pack(pady=5)

    view_btn = tk.Button(root, text="View All Guests", width=25, command=on_view)
    view_btn.pack(pady=5)

    exit_btn = tk.Button(root, text="Exit", width=25, command=root.quit)
    exit_btn.pack(pady=20)

    root.mainloop()

# ---------- Run the GUI ----------
if __name__ == "__main__":
    setup_gui()
