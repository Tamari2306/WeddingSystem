from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response
from werkzeug.utils import secure_filename
from models import Base, Guest, SessionLocal, engine  # Reuse centralized model
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
import os, qrcode, csv, zipfile, logging
from io import BytesIO, StringIO
from datetime import datetime
from functools import wraps

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = "supersecretkey123"
UPLOAD_FOLDER = "uploads"
QR_FOLDER_WEB = 'static/qr_codes'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['QR_FOLDER_WEB'] = QR_FOLDER_WEB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER_WEB, exist_ok=True)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

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


# --- Main Entry ---
if __name__ == '__main__':
    if not os.path.exists('guests.db'):
        Base.metadata.create_all(engine)
        print("Database initialized.")
    app.run(debug=True, host='0.0.0.0')
