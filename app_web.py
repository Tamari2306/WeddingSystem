from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response
from werkzeug.utils import secure_filename
from models import Base, Guest, SessionLocal, engine  # Reuse centralized model
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
import os, qrcode, csv, zipfile, logging
from io import BytesIO, StringIO
from datetime import datetime
from functools import wraps
from PIL import Image, ImageDraw, ImageFont
import os, textwrap, shutil
from dotenv import load_dotenv
from config import DevelopmentConfig, ProductionConfig


load_dotenv()  # Load environment variables from .env if it exists

# --- Flask App Setup ---
app = Flask(__name__)
env = os.getenv("FLASK_ENV", "development")

if env == "production":
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

UPLOAD_FOLDER = "uploads"
QR_FOLDER_WEB = 'static/qr_codes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['QR_FOLDER_WEB'] = QR_FOLDER_WEB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER_WEB, exist_ok=True)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Read credentials from environment or fallback
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "WedSy#01")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_guest_id():
    session = SessionLocal()
    try:
        while True:
            next_number = session.query(func.max(Guest.id)).scalar() or 0
            qr_code_id = f"GUEST-{next_number + 1:04d}"
            if not session.query(Guest).filter_by(qr_code_id=qr_code_id).first():
                return qr_code_id
    finally:
        session.close()

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

@app.route('/')
@login_required
def view_all():
    session = SessionLocal()
    try:
        guests = session.query(Guest).order_by(Guest.visual_id).all()
        return render_template('guests.html', guests=guests)
    finally:
        session.close()

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

        file_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(file_path)
        session = SessionLocal()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                next_visual_id = session.query(func.max(Guest.visual_id)).scalar() or 0
                imported, duplicates = 0, 0

                for row in reader:
                    name, phone = row.get('name'), row.get('phone')
                    if name and phone and not session.query(Guest).filter_by(phone=phone).first():
                        qr_code_id = generate_guest_id()
                        sanitized = "".join(c if c.isalnum() else '_' for c in name)
                        qr_file = os.path.join(QR_FOLDER_WEB, f"{qr_code_id}-{sanitized}.png")
                        generate_qr_code(qr_code_id, qr_file)
                        guest = Guest(
                            name=name,
                            phone=phone,
                            qr_code_id=qr_code_id,
                            qr_code_url=f"/static/qr_codes/{qr_code_id}-{sanitized}.png",
                            visual_id=next_visual_id + 1
                        )
                        try:
                            session.add(guest)
                            session.commit()
                            next_visual_id += 1
                            imported += 1
                        except IntegrityError:
                            session.rollback()
                            duplicates += 1
                    else:
                        duplicates += 1

                flash(f"{imported} guests imported, {duplicates} duplicates skipped.", 'info')
                return redirect(url_for('view_all'))
        finally:
            session.close()
            os.remove(file_path)
    return render_template('upload_csv.html')

@app.route('/download_csv')
@login_required
def download_csv():
    session = SessionLocal()
    try:
        guests = session.query(Guest).all()
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['ID', 'Name', 'Phone', 'QR Code ID', 'Has Entered', 'Entry Time', 'Visual ID'])
        for g in guests:
            cw.writerow([g.id, g.name, g.phone, g.qr_code_id, g.has_entered, g.entry_time, g.visual_id])
        output = make_response(si.getvalue())
        output.headers['Content-Disposition'] = 'attachment; filename=guests.csv'
        output.headers['Content-type'] = 'text/csv'
        return output
    finally:
        session.close()

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
    db_session = SessionLocal()
    try:
        guest = db_session.query(Guest).get(guest_id)
        if not guest:
            flash("Guest not found.", "danger")
            return redirect(url_for('view_all'))

        if request.method == 'POST':
            guest.name = request.form['name']
            guest.phone = request.form['phone']
            db_session.commit()
            flash('Guest updated successfully.')
            return redirect(url_for('view_all'))

        return render_template('edit_guest.html', guest=guest)
    finally:
        db_session.close()

# ----- Scan QR -----
@app.route('/scan_qr')
@login_required
def scan_qr():
    return render_template('scan_qr.html')


# ----- Delete -----
@app.route('/delete_guest/<int:guest_id>', methods=['GET'])
@login_required
def delete_guest(guest_id):
    db_session = SessionLocal()
    try:
        guest = db_session.query(Guest).get(guest_id)
        if not guest:
            flash("Guest not found.", "danger")
            return redirect(url_for('view_all'))

        # Delete associated QR code file
        qr_file = os.path.join(app.root_path, guest.qr_code_url.strip('/'))
        if os.path.exists(qr_file):
            os.remove(qr_file)

        db_session.delete(guest)
        db_session.commit()
        flash('Guest and QR code deleted.')
        return redirect(url_for('view_all'))
    finally:
        db_session.close()


# ----- Regenerate QR -----
@app.route('/regenerate_qr_codes')
@login_required
def regenerate_qr_codes():
    session = SessionLocal()
    try:
        guests = session.query(Guest).all()
        for guest in guests:
            sanitized = "".join(c if c.isalnum() else '_' for c in guest.name)
            qr_file = os.path.join(QR_FOLDER_WEB, f"{guest.qr_code_id}-{sanitized}.png")
            generate_qr_code(guest.qr_code_id, qr_file)
            guest.qr_code_url = f"/static/qr_codes/{guest.qr_code_id}-{sanitized}.png"
        session.commit()
        flash("QR codes regenerated.", "success")
    finally:
        session.close()
    return redirect(url_for('view_all'))


@app.route('/update_status', methods=['POST'])
@login_required
def update_status():
    data = request.get_json()
    qr_code_id = data.get("qr_code_id")

    session = SessionLocal()
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
    finally:
        session.close()

#generate_guest_cards route
@app.route('/generate_guest_cards')
@login_required
def generate_guest_cards():
    session = SessionLocal()
    try:
        template_path = os.path.join("static", "Card Template.png")
        output_folder = os.path.join("static", "guest_cards")

       # Clear old cards without deleting the folder
        for file in os.listdir(output_folder):
            file_path = os.path.join(output_folder, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                flash(f"Could not delete old card {file}: {e}", "warning")


        guests = session.query(Guest).all()
        font_path = os.path.join("static", "fonts", "29lt-riwaya-regular.ttf")
        name_font = ImageFont.truetype(font_path, 80)

        for guest in guests:
            img = Image.open(template_path).convert("RGB")
            draw = ImageDraw.Draw(img)
            W, H = img.size

            # Wrap and center name
            wrapped_name = textwrap.fill(guest.name.upper(), width=20)
            lines = wrapped_name.split('\n')
            line_height = name_font.getbbox("A")[3] + 10
            total_text_height = line_height * len(lines)
            start_y = 800 - total_text_height // 2

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=name_font)
                line_width = bbox[2] - bbox[0]
                x = (W - line_width) // 2
                y = start_y + i * line_height
                draw.text((x, y), line, font=name_font, fill="#000000")

            # Paste QR code
            qr_path = guest.qr_code_url.strip("/")
            qr_img = Image.open(qr_path).resize((320, 320))
            qr_x = (W - qr_img.width) // 2
            qr_y = 1400
            img.paste(qr_img, (qr_x, qr_y))

            # Save card with guest name
            safe_filename = f"{guest.name.upper().replace(' ', '_')}.png"
            img.save(os.path.join(output_folder, safe_filename))

        flash("Guest invitation cards generated successfully.", "success")

    except Exception as e:
        flash(f"Error generating cards: {str(e)}", "danger")
    finally:
        session.close()

    return redirect(url_for('view_all'))

#download each guest's card
@app.route('/download_card/<string:filename>')
@login_required
def download_card(filename):
    """
    Sends the requested guest card file to the user for download.

    Args:
        filename (str): The name of the guest card file to download.
    """
    output_folder = os.path.join("static", "guest_cards")
    file_path = os.path.join(output_folder, filename)

    if not os.path.isfile(file_path):
        flash("Card not found for download.", "danger")
        return redirect(url_for('view_all'))  #  You'll need a view_all route

    # Corrected send_file:
    return send_file(
        file_path,  #  Use the full file path.
        as_attachment=True,
        download_name=filename  #  Use the original filename
    )


#download_all_cards route
@app.route('/download_all_cards')
@login_required
def download_all_cards():
    output_folder = os.path.join("static", "guest_cards")
    
    if not os.path.exists(output_folder):
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

# --- Main Entry ---
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)