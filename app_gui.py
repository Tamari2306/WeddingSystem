import tkinter as tk
from tkinter import filedialog, messagebox
import csv
import os
import qrcode
import zipfile
from tkinter import ttk  # Import the themed tkinter module
from PIL import Image, ImageTk  # Import Pillow for image handling
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func  # Import func for max()
import logging
import time  # Import the time module

# --- Database Setup (Simplified) ---
Base = declarative_base()
engine = create_engine('sqlite:///guests.db')  # Use the same database file
Session = sessionmaker(bind=engine)

class Guest(Base):
    __tablename__ = 'guests'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True)
    qr_code_id = Column(String, unique=True)
    qr_code_url = Column(String)
    has_entered = Column(Boolean, default=False)
    entry_time = Column(DateTime)

Base.metadata.create_all(engine)  # Create tables if they don't exist
# --- End Database Setup ---

QR_CODE_DIR = "static/qr_codes"
os.makedirs(QR_CODE_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.DEBUG,  # Keep at DEBUG for detailed logging
                    format='%(asctime)s - %(levelname)s - %(message)s')

def generate_guest_id_gui():
    """Generates a unique guest ID in the format 'GUEST-XXXX'."""
    session = Session()  # Use a new session
    try:
        for attempt in range(5):  # limit the number of attempts to avoid infinite loops.
            next_number = session.query(func.max(Guest.id)).scalar()
            if next_number is None:
                next_number = 1
            else:
                next_number += 1
            qr_code_id = f"GUEST-{next_number:04d}"
            # Check if this ID already exists
            existing_guest = session.query(Guest).filter_by(qr_code_id=qr_code_id).first()
            if not existing_guest:
                return qr_code_id  # If it doesn't exist, use it.
            else:
                logging.warning(f"Duplicate QR Code ID: {qr_code_id}.  Attempt {attempt + 1} to generate a unique ID.")
                time.sleep(1)  # Add a small delay before retrying
        logging.error("Failed to generate a unique QR code ID after 5 attempts.")
        return None  # Return None if a unique ID cannot be generated.
    finally:
        session.close()



def import_guests_from_csv_gui():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        session = Session()
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                imported_count = 0
                new_guests = [] # keep track of guests
                for row in reader:
                    name = row.get('name')
                    phone = row.get('phone')
                    if name and phone:
                        qr_code_id = generate_guest_id_gui()
                        if qr_code_id is None:
                            logging.error(f"Failed to import guest {name}, {phone} due to repeated failure to generate unique QR code.")
                            messagebox.showerror("Error", f"Failed to import guest {name}, {phone} due to repeated failure to generate unique QR code.")
                            continue  # Skip to the next guest
                        logging.debug(f"Generated QR Code ID: {qr_code_id} for {name}, {phone}")  # Log

                        # Check for duplicate qr_code_id in the current import batch
                        if any(imported_guest.qr_code_id == qr_code_id for imported_guest in new_guests):
                            logging.error(f"Duplicate QR Code ID {qr_code_id} found in current import batch for guest: {name}, {phone}")
                            messagebox.showerror("Error", f"Duplicate QR Code ID {qr_code_id} found in current import batch for guest: {name}, {phone}")
                            continue

                        sanitized_name = "".join(c if c.isalnum() else "_" for c in name)
                        filename = os.path.join(QR_CODE_DIR, f"{qr_code_id}-{sanitized_name}.png")
                        qr = qrcode.QRCode(
                            version=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_H,
                            box_size=10,
                            border=4,
                        )
                        qr.add_data(qr_code_id)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        try:
                            img.save(filename)
                            qr_code_url = f"/static/qr_codes/{qr_code_id}-{sanitized_name}.png"
                            guest = Guest(name=name, phone=phone, qr_code_id=qr_code_id, qr_code_url=qr_code_url)
                            session.add(guest)
                            new_guests.append(guest) # append
                            imported_count += 1
                        except IOError:
                            messagebox.showerror("Error", f"Could not save QR code for {name}.")
                session.commit()
                messagebox.showinfo("Success", f"{imported_count} guests imported and QR code information generated.")
        except FileNotFoundError:
            messagebox.showerror("Error", "CSV file not found.")
        except Exception as e:
            session.rollback()
            logging.error(f"An error occurred during import: {e}", exc_info=True)  # Log the error with traceback
            messagebox.showerror("Error", f"An error occurred during import: {e}")
        finally:
            session.close()



def export_guests_to_csv_gui():
    file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
    if file_path:
        session = Session()
        try:
            guests = session.query(Guest).all()
            exported_count = 0
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["id", "name", "phone", "qr_code_id", "qr_code_url", "has_entered"])
                for guest in guests:
                    writer.writerow([guest.id, guest.name, guest.phone, guest.qr_code_id, guest.qr_code_url, guest.has_entered])
                    exported_count += 1
            messagebox.showinfo("Success", f"{exported_count} guests exported successfully.")
        except Exception as e:
            session.rollback()
            logging.error(f"Error during export: {e}", exc_info=True)
            messagebox.showerror("Error", f"An error occurred during export: {e}")
        finally:
            session.close()

def generate_qr_codes_gui():
    session = Session()
    try:
        guests = session.query(Guest).all()
        generated_count = 0
        deleted_count = 0

        # Delete existing QR code images
        for guest in guests:
            if guest.qr_code_url:
                old_image_path = os.path.join(".", guest.qr_code_url.lstrip("/"))
                try:
                    os.remove(old_image_path)
                    print(f"Deleted old QR code: {old_image_path}")
                    deleted_count += 1
                except FileNotFoundError:
                    print(f"Old QR code not found: {old_image_path}")
                except Exception as e:
                    logging.error(f"Error deleting old QR code for {guest.name}: {e}", exc_info=True)
                    messagebox.showerror("Error", f"Error deleting old QR code for {guest.name}: {e}")

        # Generate new QR code images
        for guest in guests:
            if not guest.qr_code_id:
                guest.qr_code_id = generate_guest_id_gui()
            if guest.qr_code_id is None:
                logging.error(f"Failed to generate QR code for guest ID {guest.id} and Name {guest.name}." )
                continue
            sanitized_name = "".join(c if c.isalnum() else "_" for c in guest.name)
            filename = os.path.join(QR_CODE_DIR, f"{guest.qr_code_id}-{sanitized_name}.png")
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(guest.qr_code_id)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            try:
                img.save(filename)
                guest.qr_code_url = f"/static/qr_codes/{guest.qr_code_id}-{sanitized_name}.png"
                generated_count += 1
            except IOError:
                logging.error(f"Could not save QR code for guest ID {guest.id}.", exc_info=True)
                messagebox.showerror("Error", f"Could not save QR code for guest ID {guest.id}.")

        session.commit()
        messagebox.showinfo("Success", f"{deleted_count} old QR codes deleted and {generated_count} new QR codes generated/updated in '{QR_CODE_DIR}'.")
    finally:
        session.close()

def zip_all_qr_codes_gui():
    zip_filename = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("Zip Files", "*.zip")])
    if zip_filename:
        try:
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                found_files = []
                for root_dir, _, files in os.walk(QR_CODE_DIR):
                    for file in files:
                        file_path = os.path.join(root_dir, file)
                        arcname = os.path.relpath(file_path, QR_CODE_DIR)
                        zipf.write(file_path, arcname=arcname)
                        found_files.append(file_path)
                print(f"Files found for zipping: {found_files=}")
            messagebox.showinfo("Success", f"{len(found_files)} QR codes zipped successfully.")
        except Exception as e:
            logging.error(f"An error occurred during zipping: {e}", exc_info=True)
            messagebox.showerror("Error", f"An error occurred during zipping: {e}")

def view_all_guests_gui():
    session = Session()
    try:
        guests = session.query(Guest).all()
        if not guests:
            messagebox.showinfo("Guest List", "No guests found.")
            return

        top = tk.Toplevel()
        top.title("Guest List")

        tree = ttk.Treeview(top, columns=("visual_id", "id", "name", "phone", "qr_code_id", "qr_code_url", "has_entered", "qr_image"), show="headings")
        tree.heading("visual_id", text="Visual ID")  # Add Visual ID Column
        tree.heading("id", text="ID")
        tree.heading("name", text="Name")
        tree.heading("phone", text="Phone")
        tree.heading("qr_code_id", text="QR Code ID")
        tree.heading("qr_code_url", text="QR Code URL")
        tree.heading("has_entered", text="Entered?")
        tree.heading("qr_image", text="QR Code Image")  # Header for the image column
        tree.column("visual_id", width=50)

        for index, guest in enumerate(guests, start=1):  # Add visual index
            img = None
            try:
                img_path = os.path.join(".", guest.qr_code_url.lstrip("/"))
                img_pil = Image.open(img_path)
                img_resized = img_pil.resize((50, 50), Image.Resampling.LANCZOS)
                img = ImageTk.PhotoImage(img_resized)
                tree.insert("", tk.END, values=(index, guest.id, guest.name, guest.phone, guest.qr_code_id, guest.qr_code_url, "Yes" if guest.has_entered else "No", img))
                tree.image = img  # Keep a reference
            except FileNotFoundError:
                tree.insert("", tk.END, values=(index, guest.id, guest.name, guest.phone, guest.qr_code_id, guest.qr_code_url, "Yes" if guest.has_entered else "No", "Image Not Found"))
            except Exception as e:
                tree.insert("", tk.END, values=(index, guest.id, guest.name, guest.phone, guest.qr_code_id, guest.qr_code_url, "Yes" if guest.has_entered else "No", f"Error: {e}"))

        tree.pack(expand=True, fill="both")

        # Add Delete button
        delete_button = ttk.Button(top, text="Delete Guest", command=lambda: delete_selected_guest(tree, top))
        delete_button.pack(pady=10)

    finally:
        session.close()

def delete_selected_guest(tree, top):
    """Deletes the selected guest from the database and updates the treeview."""
    session = Session()
    try:
        selected_item = tree.selection()  # Get selected item ID
        if not selected_item:
            messagebox.showinfo("Error", "Please select a guest to delete.")
            return

        guest_id = tree.item(selected_item, 'values')[1]  # Get guest ID from the selected row's values (ID is at index 1)
        guest_to_delete = session.query(Guest).filter_by(id=guest_id).first()

        if guest_to_delete:
            qr_code_url = guest_to_delete.qr_code_url
            if qr_code_url:
                image_path = os.path.join(".", qr_code_url.lstrip("/"))
                try:
                    os.remove(image_path)
                    print(f"Deleted QR code: {image_path}")
                except FileNotFoundError:
                    print(f"QR code not found: {image_path}")
                except Exception as e:
                    logging.error(f"Error deleting QR code: {e}", exc_info=True)
                    messagebox.showerror("Error", f"Error deleting QR code: {e}")

            session.delete(guest_to_delete)
            session.commit()
            messagebox.showinfo("Success", f'Guest "{guest_to_delete.name}" deleted successfully.', parent=top)
            update_visual_ids(tree)  # Update visual IDs in the treeview
        else:
            messagebox.showinfo("Error", "Guest not found.", parent=top)
    except Exception as e:
        session.rollback()
        logging.error(f"An error occurred while deleting the guest: {e}", exc_info=True)
        messagebox.showerror("Error", f"An error occurred while deleting the guest: {e}", parent=top)
    finally:
        session.close()
    # Destroy the top level window after deletion.
    top.destroy()

def update_visual_ids(tree):
    """Updates the visual IDs in the treeview after a deletion."""
    guests = []
    for item in tree.get_children():
        guest_data = tree.item(item, 'values')
        guests.append(guest_data[1:])  # Exclude the old visual ID, keep other guest data
    tree.delete(*tree.get_children())  # Clear all items in the treeview

    for index, guest_data in enumerate(guests, start=1):
        img = None
        try:
            img_path = os.path.join(".", guest_data[4].lstrip("/")) #guest_data[4] is qr_code_url
            img_pil = Image.open(img_path)
            img_resized = img_pil.resize((50, 50), Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(img_resized)
            tree.insert("", tk.END, values=(index,) + guest_data[:])
            tree.image = img
        except FileNotFoundError:
             tree.insert("", tk.END, values=(index,) + guest_data[:4] + ("Image Not Found",) + guest_data[5:])
        except:
            tree.insert("", tk.END, values=(index,) + guest_data[:4] + ("Error",) + guest_data[5:])

def main_gui():
    root = tk.Tk()
    root.title("Guest Management System")

    ttk.Button(root, text="📥 Import Guests & Generate QR", command=import_guests_from_csv_gui, width=40).pack(pady=5)
    ttk.Button(root, text="✨ Generate/Update QR Codes", command=generate_qr_codes_gui, width=40).pack(pady=5)
    ttk.Button(root, text="📤 Export Guests to CSV", command=export_guests_to_csv_gui, width=40).pack(pady=5)
    ttk.Button(root, text="🗜️ Zip All QR Codes", command=zip_all_qr_codes_gui, width=40).pack(pady=5)
    ttk.Button(root, text="📋 View All Guests", command=view_all_guests_gui, width=40).pack(pady=5)
    ttk.Button(root, text="❌ Exit", command=root.quit, width=40).pack(pady=20)

    root.mainloop()


if __name__ == "__main__":
    main_gui()
