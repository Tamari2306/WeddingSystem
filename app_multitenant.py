import os
import json
import textwrap
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from sqlalchemy import event, DDL
from PIL import Image, ImageDraw, ImageFont
from werkzeug.security import generate_password_hash # Added for robust password handling
from uuid import uuid4

# --- Initialize Flask App ---
# NOTE: This app uses a separate configuration and file structure to avoid conflict with your main app.
app = Flask(__name__)
app.config['SECRET_KEY'] = 'multitenant_test_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_multitenant_guests.db' # Using a new DB file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['GUEST_CARDS_FOLDER'] = os.path.join('static', 'guest_cards_test')
app.config['QR_CODES_FOLDER'] = os.path.join('static', 'qrcodes_test')

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure required folders exist
os.makedirs(app.config['GUEST_CARDS_FOLDER'], exist_ok=True)
os.makedirs(app.config['QR_CODES_FOLDER'], exist_ok=True)
os.makedirs(os.path.join('static', 'fonts'), exist_ok=True) # Ensure fonts folder is there

# --- Configuration Constants ---
FONT_PATH = os.path.join("static", "fonts", "Roboto-Bold.ttf")


# --- Database Models (Updated for Multi-Client/Multi-Event) ---

# Junction Table for Guest to Event Access (Many-to-Many)
guest_event_access = db.Table('guest_event_access',
    db.Column('guest_id', db.Integer, db.ForeignKey('guest.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    # Storing hashed password is best practice, using clear text for quick demo simplicity if necessary.
    password = db.Column(db.String(100), nullable=False) 

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    events = db.relationship('Event', backref='client', lazy=True)
    guests = db.relationship('Guest', backref='client', lazy=True)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    checkins = db.relationship('CheckIn', backref='event', lazy=True)

class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False) 
    name = db.Column(db.String(100), nullable=False)
    visual_id = db.Column(db.Integer, nullable=False) # visual_id no longer needs to be unique globally, only per client
    qr_code_id = db.Column(db.String(50), unique=True, nullable=False)
    qr_code_url = db.Column(db.String(200))
    card_type = db.Column(db.String(50))
    # Relationships
    check_ins = db.relationship('CheckIn', backref='guest', lazy=True)
    events = db.relationship('Event', secondary=guest_event_access, 
                             backref=db.backref('attendees', lazy='dynamic')) 

class CheckIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Database Initialization and Mock Data (for testing) ---
with app.app_context():
    db.create_all()

    # Create a default user if none exists
    if not User.query.first():
        # Using generate_password_hash for better practice, though simple string comparison in login route
        # is kept for consistency with your original simplified demo logic.
        hashed_password = generate_password_hash('admin', method='pbkdf2:sha256') 
        default_user = User(username='admin', password='admin') # Storing as plain text for simple demo login
        db.session.add(default_user)
        db.session.commit()
    
    # Create two different mock clients and their events
    if not Client.query.first():
        # Client 1: The Smith Wedding (Two events)
        client1 = Client(name="The Smith Wedding")
        db.session.add(client1)
        db.session.commit()
        
        event1_a = Event(client_id=client1.id, name="Rehearsal Dinner")
        event1_b = Event(client_id=client1.id, name="Wedding Ceremony")
        db.session.add_all([event1_a, event1_b])
        db.session.commit()

        guest1 = Guest(client_id=client1.id, name="John Doe", visual_id=1001, qr_code_id=str(uuid4()), qr_code_url=f"/static/qrcodes_test/{str(uuid4())}.png", card_type="VIP")
        guest2 = Guest(client_id=client1.id, name="Jane Smith", visual_id=1002, qr_code_id=str(uuid4()), qr_code_url=f"/static/qrcodes_test/{str(uuid4())}.png", card_type="Standard")
        
        # Grant access: John to Rehearsal & Ceremony, Jane to Ceremony only
        guest1.events.extend([event1_a, event1_b])
        guest2.events.append(event1_b)
        db.session.add_all([guest1, guest2])
        db.session.commit()

        # Client 2: Acme Corp (One event)
        client2 = Client(name="Acme Corp Annual Gala")
        db.session.add(client2)
        db.session.commit()

        event2_a = Event(client_id=client2.id, name="Annual Gala Check-In")
        db.session.add(event2_a)
        db.session.commit()
        
        guest3 = Guest(client_id=client2.id, name="CEO Max Power", visual_id=2001, qr_code_id=str(uuid4()), qr_code_url=f"/static/qrcodes_test/{str(uuid4())}.png", card_type="Executive")
        guest4 = Guest(client_id=client2.id, name="Manager Liz Lemon", visual_id=2002, qr_code_id=str(uuid4()), qr_code_url=f"/static/qrcodes_test/{str(uuid4())}.png", card_type="Employee")
        
        # Grant access: All guests to the Gala
        guest3.events.append(event2_a)
        guest4.events.append(event2_a)
        db.session.add_all([guest3, guest4])
        db.session.commit()


# --- Helper Functions (Simplified) ---

def get_safe_filename_name_part(name):
    """Sanitizes a name string for use in a file name."""
    return "".join(c for c in name if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')

# --- Routes (Updated for Multi-Client/Multi-Event) ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        # NOTE: Using simplified password check for this test demo
        if user and user.password == request.form.get('password'): 
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # The dashboard now shows all clients and their associated events
    clients = Client.query.all()
    # Using the new multitenant index template
    return render_template('index_multitenant.html', clients=clients)

# --- CLIENT MANAGEMENT ---
@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    name = request.form.get('client_name')
    if name:
        if Client.query.filter_by(name=name).first():
            flash("Client name already exists.", 'warning')
        else:
            new_client = Client(name=name)
            db.session.add(new_client)
            db.session.commit()
            flash(f"Client '{name}' added successfully.", 'success')
    return redirect(url_for('index'))

# --- EVENT MANAGEMENT ---
@app.route('/add_event/<int:client_id>', methods=['POST'])
@login_required
def add_event(client_id):
    name = request.form.get('event_name')
    if name:
        client = Client.query.get_or_404(client_id)
        if Event.query.filter_by(client_id=client_id, name=name).first():
            flash(f"Event '{name}' already exists for client '{client.name}'.", 'warning')
        else:
            new_event = Event(client_id=client_id, name=name)
            db.session.add(new_event)
            db.session.commit()
            flash(f"Event '{name}' added successfully for {client.name}.", 'success')
    return redirect(url_for('index'))

# --- GUEST MANAGEMENT (NEW ROUTE) ---
@app.route('/add_guest/<int:client_id>', methods=['POST'])
@login_required
def add_guest(client_id):
    client = Client.query.get_or_404(client_id)
    guest_name = request.form.get('guest_name')
    visual_id_str = request.form.get('visual_id')
    card_type = request.form.get('card_type')
    event_ids = request.form.getlist('event_ids') # list of event IDs guest has access to

    try:
        visual_id = int(visual_id_str)
    except ValueError:
        flash("Visual ID must be a number.", 'danger')
        return redirect(url_for('view_all', client_id=client_id))

    # Basic validation (could be more robust)
    if not guest_name or not card_type or not visual_id_str:
        flash("All guest fields are required.", 'danger')
        return redirect(url_for('view_all', client_id=client_id))

    # Check for duplicate Visual ID within this Client
    if Guest.query.filter_by(client_id=client_id, visual_id=visual_id).first():
        flash(f"Visual ID {visual_id} already exists for client {client.name}. Please choose a unique ID.", 'danger')
        return redirect(url_for('view_all', client_id=client_id))

    # 1. Create the new guest
    # A unique QR code ID is generated here (this is what the scanner will look for)
    new_guest = Guest(
        client_id=client_id,
        name=guest_name,
        visual_id=visual_id,
        qr_code_id=str(uuid4()), # Generate a unique ID for QR code
        card_type=card_type
    )

    # 2. Assign access to selected events
    if event_ids:
        # Filter for events that belong to the current client and whose IDs were submitted
        events_to_assign = Event.query.filter(
            Event.id.in_([int(eid) for eid in event_ids]),
            Event.client_id == client_id # Ensure security: can only assign client's own events
        ).all()
        
        for event in events_to_assign:
            new_guest.events.append(event)
    
    db.session.add(new_guest)
    db.session.commit()
    
    # 3. Create a mock QR URL for display (since we can't generate images here)
    new_guest.qr_code_url = f"/static/qrcodes_test/{new_guest.qr_code_id}.png"
    db.session.commit()

    flash(f"Guest '{guest_name}' (ID: {visual_id}) added successfully and assigned to {len(new_guest.events)} events.", 'success')
    return redirect(url_for('view_all', client_id=client_id))


# --- CHECK-IN LOGIC (CRITICAL UPDATE) ---

@app.route('/scan_qr/<int:event_id>')
@login_required
def scan_qr_event(event_id):
    # Fetch the event name for display on the scanner page
    current_event = Event.query.get_or_404(event_id)
    # Using your existing scan_qr.html template (it needs the `event` object)
    return render_template('scan_qr.html', event=current_event)

@app.route('/update_status', methods=['POST'])
@login_required
def update_status():
    data = request.get_json()
    qr_code_id = data.get('qr_code_id')
    event_id = data.get('event_id') 

    if not qr_code_id or not event_id:
        return jsonify({
            'success': False,
            'message': 'Missing QR code or Event ID.',
            'already_entered': False
        }), 400

    guest = Guest.query.filter_by(qr_code_id=qr_code_id).first()
    current_event = Event.query.get(event_id)

    if not guest:
        return jsonify({
            'success': False,
            'message': 'Guest not found.',
            'already_entered': False,
            'guest': None
        })

    # 1. Check if the guest has access to this event (using the guest.events relationship)
    if current_event not in guest.events:
        return jsonify({
            'success': False,
            'message': f'Access Denied: Guest {guest.name} is not on the list for {current_event.name}.',
            'already_entered': False,
            'guest': {'id': guest.visual_id, 'name': guest.name, 'card_type': guest.card_type}
        })

    # 2. Check if the guest has already checked into this specific event
    already_checked_in = CheckIn.query.filter_by(guest_id=guest.id, event_id=event_id).first()

    guest_details = {
        'id': guest.visual_id,
        'name': guest.name,
        'card_type': guest.card_type
    }
    
    if already_checked_in:
        return jsonify({
            'success': False,
            'message': f'Guest ALREADY CHECKED IN to {current_event.name} at {already_checked_in.timestamp.strftime("%H:%M:%S")}.',
            'already_entered': True,
            'guest': guest_details
        })
    else:
        # 3. Log the new check-in
        new_check_in = CheckIn(guest_id=guest.id, event_id=event_id)
        db.session.add(new_check_in)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'CHECK-IN SUCCESSFUL for {current_event.name}.',
            'already_entered': False,
            'guest': guest_details
        })

# --- CARD GENERATION (Scoped to Client) ---

@app.route('/view_all/<int:client_id>')
@login_required
def view_all(client_id):
    client = Client.query.get_or_404(client_id)
    guests = Guest.query.filter_by(client_id=client_id).all()
    events = Event.query.filter_by(client_id=client_id).all()
    
    event_stats = []
    for event in events:
        # Check-ins count for this event
        checked_in_count = CheckIn.query.filter_by(event_id=event.id).count()
        # Total invited guests for this specific event
        total_invited = len(event.attendees.all())
        
        event_stats.append({
            'name': event.name,
            'total': total_invited,
            'checked_in': checked_in_count
        })

    # Note: view_all.html template must handle the client and event data
    return render_template('view_all.html', guests=guests, client=client, events=events, event_stats=event_stats)

@app.route('/generate_guest_cards/<int:client_id>')
@login_required
def generate_guest_cards(client_id):
    # This route remains disabled for the safe testing environment.
    flash("Card generation is disabled in this test environment to prevent file errors. Please run the check-in and dashboard features.", "info")
    return redirect(url_for('view_all', client_id=client_id))

if __name__ == '__main__':
    app.run(debug=True)
