from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response, current_app
from werkzeug.utils import secure_filename
# IMPORT THESE FROM MODELS.PY!
from models import Guest, init_db, get_db_session # Import Guest, init_db, and get_db_session
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
import os, qrcode, csv, zipfile, logging
from io import BytesIO, StringIO
from datetime import datetime
from functools import wraps
from PIL import Image, ImageDraw, ImageFont # Make sure Pillow is installed: pip install Pillow
import textwrap # For text wrapping on images
import shutil # For clearing folder, already present

# IMPORTANT: Use dotenv_values to get the values from the specific file first
from dotenv import dotenv_values, load_dotenv

# --- Environment Variable Loading Strategy ---
flask_env = os.getenv('FLASK_ENV', 'production')

if flask_env == 'development':
    current_env_file = '.env.development'
    logging.info("Loading environment from .env.development")
else:
    current_env_file = '.env'
    logging.info("Loading environment from .env")

config = dotenv_values(current_env_file)

for key, value in config.items():
    if value is not None:
        os.environ[key] = value

# --- Configuration for Database ---
# DB_FILE will now be correctly picked up from the loaded environment variables
DB_FILE = os.getenv("DB_FILE", "guests.db")
DATABASE_URL = f"sqlite:///./{DB_FILE}"

# --- Flask Application Initialization ---
app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

if not app.config['SECRET_KEY']:
    raise ValueError("SECRET_KEY environment variable is not set. "
                     "Please set a strong, random key in your .env or .env.development file.")

# Set the SQLAlchemy database URI for Flask's internal config.
# This is what `init_db(app)` will use.
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

# --- Folder Configurations ---
UPLOAD_FOLDER = "uploads"
QR_FOLDER_WEB = 'static/qr_codes'
GUEST_CARDS_FOLDER = 'static/guest_cards'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['QR_FOLDER_WEB'] = QR_FOLDER_WEB
app.config['GUEST_CARDS_FOLDER'] = GUEST_CARDS_FOLDER

# Create necessary directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER_WEB, exist_ok=True)
os.makedirs(GUEST_CARDS_FOLDER, exist_ok=True)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

logging.info(f"Using database: {DATABASE_URL}")

# --- Admin Credentials (Read from environment or fallback) ---
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "WedSy#01")

# --- Initialize the database using models.py's init_db function ---
# This must happen after app config is set, but before routes try to access DB.
# Using app.app_context() ensures Flask's context is available.
with app.app_context():
    init_db(app) # Pass the app object, so init_db can read app.config['SQLALCHEMY_DATABASE_URI']

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Helper Functions ---
# IMPORTANT: All these helper functions should now use get_db_session()
def generate_guest_id():
    with get_db_session() as session: # Use the context manager
        while True:
            next_visual_id = session.query(func.max(Guest.visual_id)).scalar() or 0
            qr_code_id_candidate = f"GUEST-{next_visual_id + 1:04d}"
            if not session.query(Guest).filter_by(qr_code_id=qr_code_id_candidate).first():
                return qr_code_id_candidate

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    return filename

# --- Routes ---
@app.route('/')
@login_required
def view_all():
    with get_db_session() as session: # Use the context manager
        guests = session.query(Guest).order_by(Guest.visual_id).all()
        return render_template('guests.html', guests=guests, current_environment=flask_env)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Login successful.', 'success')
            return redirect(url_for('view_all'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/upload_csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.csv'):
            flash('Invalid file. Please upload a CSV.', 'danger')
            return redirect(request.url)

        stream = StringIO(file.stream.read().decode("utf-8"))
        reader = csv.DictReader(stream)

        with get_db_session() as session: # Use the context manager
            try:
                next_visual_id = session.query(func.max(Guest.visual_id)).scalar() or 0
                imported, duplicates = 0, 0

                for row in reader:
                    row = {k.strip(): v.strip() for k, v in row.items()}

                    name = row.get('Name')
                    phone = row.get('Phone')
                    card_type = row.get('Card Type', 'single').lower()
                    if card_type not in ['single', 'double']:
                        card_type = 'single'

                    if not name or not phone:
                        flash(f"Skipping row due to missing Name or Phone: {row}", "warning")
                        continue

                    existing_guest = session.query(Guest).filter_by(phone=phone).first()
                    if existing_guest:
                        duplicates += 1
                        flash(f"Guest with phone {phone} (Name: {name}) already exists. Skipping.", "info")
                        continue

                    next_visual_id += 1
                    qr_code_id = f"GUEST-{next_visual_id:04d}"

                    sanitized_name = "".join(c if c.isalnum() else '_' for c in name)
                    qr_file_path = os.path.join(QR_FOLDER_WEB, f"{qr_code_id}-{sanitized_name}.png")
                    generate_qr_code(qr_code_id, qr_file_path)

                    guest = Guest(
                        name=name,
                        phone=phone,
                        qr_code_id=qr_code_id,
                        qr_code_url=f"/static/qr_codes/{qr_code_id}-{sanitized_name}.png",
                        visual_id=next_visual_id,
                        card_type=card_type
                    )

                    session.add(guest)
                    imported += 1

                session.commit()
                flash(f"{imported} guests imported, {duplicates} duplicates skipped.", 'info')
                return redirect(url_for('view_all'))
            except Exception as e:
                session.rollback()
                flash(f'Error importing CSV: {e}', 'danger')
                current_app.logger.error(f"Error importing CSV: {e}", exc_info=True)
            finally:
                # The 'with' statement handles session.close()
                pass # No need for finally: session.close() here because of 'with'

    return render_template('upload_csv.html')

@app.route('/download_csv')
@login_required
def download_csv():
    with get_db_session() as session: # Use the context manager
        guests = session.query(Guest).all()
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['ID', 'Name', 'Phone', 'QR Code ID', 'Has Entered', 'Entry Time', 'Visual ID', 'Card Type'])
        for g in guests:
            cw.writerow([g.id, g.name, g.phone, g.qr_code_id, g.has_entered, g.entry_time, g.visual_id, g.card_type])
        output = make_response(si.getvalue())
        output.headers['Content-Disposition'] = 'attachment; filename=guests.csv'
        output.headers['Content-type'] = 'text/csv'
        return output

@app.route('/zip_qr_codes_web')
@login_required
def zip_qr_codes_web():
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for filename in os.listdir(QR_FOLDER_WEB):
            path = os.path.join(QR_FOLDER_WEB, filename)
            if os.path.isfile(path):
                zf.write(path, filename)
    memory_file.seek(0)
    return send_file(memory_file, download_name='qr_codes.zip', as_attachment=True, mimetype='application/zip')


# ----- Edit Guest -----
@app.route('/edit_guest/<int:guest_id>', methods=['GET', 'POST'])
@login_required
def edit_guest(guest_id):
    with get_db_session() as session: # Use the context manager
        try:
            guest = session.query(Guest).get(guest_id)
            if not guest:
                flash("Guest not found.", "danger")
                return redirect(url_for('view_all'))

            if request.method == 'POST':
                guest.name = request.form['name']
                guest.phone = request.form['phone']
                guest.has_entered = 'has_entered' in request.form
                guest.card_type = request.form['card_type']

                session.commit()
                flash('Guest updated successfully.', 'success')
                return redirect(url_for('view_all'))

            return render_template('edit_guest.html', guest=guest)
        except Exception as e:
            session.rollback()
            flash(f'Error updating guest: {e}', 'danger')
            current_app.logger.error(f"Error updating guest {guest_id}: {e}", exc_info=True)
            return redirect(url_for('view_all'))


# ----- Scan QR -----
@app.route('/scan_qr')
@login_required
def scan_qr():
    return render_template('scan_qr.html')


# ----- Delete Individual Guest -----
@app.route('/delete_guest/<int:guest_id>', methods=['GET'])
@login_required
def delete_guest(guest_id):
    with get_db_session() as session: # Use the context manager
        try:
            guest = session.query(Guest).get(guest_id)
            if not guest:
                flash("Guest not found.", "danger")
                return redirect(url_for('view_all'))

            # Delete associated QR code file
            qr_file_relative_path = guest.qr_code_url.lstrip('/')
            qr_file_abs_path = os.path.join(current_app.root_path, qr_file_relative_path)

            if os.path.exists(qr_file_abs_path):
                os.remove(qr_file_abs_path)
                current_app.logger.info(f"Deleted QR file: {qr_file_abs_path}")
            else:
                current_app.logger.warning(f"QR file not found for deletion: {qr_file_abs_path}")

            # --- Delete Guest Card (if it exists) ---
            sanitized_name = guest.name.upper().replace(' ', '_')
            guest_card_filename = f"GUEST-{guest.visual_id:04d}-{sanitized_name}.png"
            guest_card_path = os.path.join(GUEST_CARDS_FOLDER, guest_card_filename)
            if os.path.exists(guest_card_path):
                os.remove(guest_card_path)
                current_app.logger.info(f"Deleted guest card: {guest_card_path}")
            else:
                current_app.logger.warning(f"Guest card not found for deletion: {guest_card_path}")

            session.delete(guest)
            session.commit()
            flash('Guest and associated files deleted.', 'success')
            return redirect(url_for('view_all'))
        except Exception as e:
            session.rollback()
            flash(f'Error deleting guest: {e}', 'danger')
            current_app.logger.error(f"Error deleting guest {guest_id}: {e}", exc_info=True)
            return redirect(url_for('view_all'))


# ----- Regenerate QR -----
@app.route('/regenerate_qr_codes')
@login_required
def regenerate_qr_codes():
    with get_db_session() as session: # Use the context manager
        try:
            guests = session.query(Guest).all()
            for guest in guests:
                qr_code_id = f"GUEST-{guest.visual_id:04d}"
                sanitized_name = "".join(c if c.isalnum() else '_' for c in guest.name)

                qr_file_path = os.path.join(QR_FOLDER_WEB, f"{qr_code_id}-{sanitized_name}.png")
                generate_qr_code(qr_code_id, qr_file_path)

                guest.qr_code_id = qr_code_id
                guest.qr_code_url = f"/static/qr_codes/{qr_code_id}-{sanitized_name}.png"
            session.commit()
            flash("QR codes regenerated.", "success")
        except Exception as e:
            session.rollback()
            flash(f"Error regenerating QR codes: {e}", "danger")
            current_app.logger.error(f"Error regenerating QR codes: {e}", exc_info=True)
    return redirect(url_for('view_all'))


@app.route('/update_status', methods=['POST'])
@login_required
def update_status():
    data = request.get_json()
    qr_code_id = data.get("qr_code_id")

    with get_db_session() as session: # Use the context manager
        try:
            guest = session.query(Guest).filter_by(qr_code_id=qr_code_id).first()
            if not guest:
                return jsonify(success=False, message="Guest not found.")

            if guest.has_entered:
                return jsonify(success=False, already_entered=True, message="Guest already checked in.")

            guest.has_entered = True
            guest.entry_time = datetime.now()
            session.commit()
            return jsonify(success=True, message=f"{guest.name} successfully checked in.")
        except Exception as e:
            session.rollback()
            current_app.logger.error(f"Error updating status for {qr_code_id}: {e}", exc_info=True)
            return jsonify(success=False, message=f"An error occurred: {e}")


#generate_guest_cards route
@app.route('/generate_guest_cards')
@login_required
def generate_guest_cards():
    with get_db_session() as session: # Use the context manager
        try:
            template_path = os.path.join("static", "Card Template.png")
            output_folder = current_app.config['GUEST_CARDS_FOLDER']

            for file in os.listdir(output_folder):
                file_path = os.path.join(output_folder, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    flash(f"Could not delete old card {file}: {e}", "warning")
                    current_app.logger.warning(f"Failed to delete old card {file}: {e}")

            guests = session.query(Guest).all()
            font_path = os.path.join("static", "fonts", "29lt-riwaya-regular.ttf")

            if not os.path.exists(font_path):
                raise FileNotFoundError(f"Font file not found at: {font_path}. Please ensure it exists.")

            name_font = ImageFont.truetype(font_path, 80)
            card_type_font = ImageFont.truetype(font_path, 50)

            for guest in guests:
                img = Image.open(template_path).convert("RGB")
                draw = ImageDraw.Draw(img)
                W, H = img.size

                wrapped_name = textwrap.fill(guest.name.upper(), width=20)
                lines = wrapped_name.split('\n')
                line_height = name_font.getbbox("A")[3] + 10
                total_text_height = line_height * len(lines)

                name_y_start = 800 - total_text_height // 2

                for i, line in enumerate(lines):
                    bbox = draw.textbbox((0, 0), line, font=name_font)
                    line_width = bbox[2] - bbox[0]
                    x = (W - line_width) // 2
                    y = name_y_start + i * line_height
                    draw.text((x, y), line, font=name_font, fill="#000000")

                qr_file_relative_path = guest.qr_code_url.lstrip('/')
                qr_file_abs_path = os.path.join(current_app.root_path, qr_file_relative_path)

                if not os.path.exists(qr_file_abs_path):
                        current_app.logger.warning(f"QR code file not found for guest {guest.name}: {qr_file_abs_path}. Skipping card generation.")
                        continue

                qr_img = Image.open(qr_file_abs_path).resize((320, 320))
                qr_x = (W - qr_img.width) // 2
                qr_y = 1350
                img.paste(qr_img, (qr_x, qr_y))

                card_type_text = guest.card_type.upper()

                card_type_bbox = draw.textbbox((0, 0), card_type_text, font=card_type_font)
                card_type_width = card_type_bbox[2] - card_type_bbox[0]
                right_margin = 130
                card_type_x = W - card_type_width - right_margin
                card_type_y = qr_y + total_text_height + 220

                draw.text((card_type_x, card_type_y), card_type_text, font=card_type_font, fill="#FF0000")

                sanitized_filename = f"GUEST-{guest.visual_id:04d}-{guest.name.upper().replace(' ', '_')}.png"
                img.save(os.path.join(output_folder, sanitized_filename))

            flash("Guest invitation cards generated successfully.", "success")

        except FileNotFoundError as fnfe:
            flash(f"Required file not found: {str(fnfe)}", "danger")
            current_app.logger.error(f"File not found during card generation: {fnfe}", exc_info=True)
        except Exception as e:
            flash(f"Error generating cards: {str(e)}", "danger")
            current_app.logger.error(f"Error generating cards: {e}", exc_info=True)
    return redirect(url_for('view_all'))

#download each guest's card
@app.route('/download_card/<string:filename>')
@login_required
def download_card(filename):
    output_folder = current_app.config['GUEST_CARDS_FOLDER']

    file_path = os.path.join(output_folder, filename)

    if not os.path.isfile(file_path):
        flash(f"Card not found for download: '{filename}'. Please ensure the file exists.", "danger")
        current_app.logger.error(f"FileNotFoundError: Attempted to download '{file_path}' but it does not exist.")
        return redirect(url_for('view_all'))

    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename
    )

#download_all_cards route
@app.route('/download_all_cards')
@login_required
def download_all_cards():
    output_folder = current_app.config['GUEST_CARDS_FOLDER']

    if not os.path.exists(output_folder) or not os.listdir(output_folder):
        flash("No invitation cards found. Please generate them first.", "warning")
        return redirect(url_for('view_all'))

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename in os.listdir(output_folder):
            path = os.path.join(output_folder, filename)
            if os.path.isfile(path):
                zip_file.write(path, arcname=filename)

    zip_buffer.seek(0)
    return send_file(zip_buffer, download_name="invitation_cards.zip", as_attachment=True)

# ----- Clear All Data Route (NEW) -----
@app.route('/clear_all_data', methods=['GET'])
@login_required
def clear_all_data():
    with get_db_session() as session: # Use the context manager
        try:
            num_deleted_guests = session.query(Guest).delete()
            session.commit()
            flash(f"Successfully deleted {num_deleted_guests} guests from the database.", "success")
            current_app.logger.info(f"Cleared {num_deleted_guests} guests from {DATABASE_URL}")

            qr_folder = current_app.config['QR_FOLDER_WEB']
            for filename in os.listdir(qr_folder):
                file_path = os.path.join(qr_folder, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    current_app.logger.error(f"Error deleting QR file {file_path}: {e}")
                    flash(f"Error deleting QR file {filename}: {e}", "warning")
            flash(f"Cleared QR codes from '{qr_folder}'.", "success")
            current_app.logger.info(f"Cleared QR codes from {qr_folder}")

            guest_cards_folder = current_app.config['GUEST_CARDS_FOLDER']
            for filename in os.listdir(guest_cards_folder):
                file_path = os.path.join(guest_cards_folder, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    current_app.logger.error(f"Error deleting guest card {file_path}: {e}")
                    flash(f"Error deleting guest card {filename}: {e}", "warning")
            flash(f"Cleared guest cards from '{guest_cards_folder}'.", "success")
            current_app.logger.info(f"Cleared guest cards from {guest_cards_folder}")

            return redirect(url_for('view_all'))

        except Exception as e:
            session.rollback()
            flash(f"An error occurred while clearing data: {e}", "danger")
            current_app.logger.error(f"Error clearing all data: {e}", exc_info=True)
            return redirect(url_for('view_all'))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)