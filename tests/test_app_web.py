import pytest
from unittest.mock import patch, MagicMock
from models import Guest, get_db_session # Import get_db_session
import os
from datetime import datetime

# The `client` fixture from conftest.py implicitly sets up the Flask app and patches
# `get_db_session` to use the test database.

def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome" in response.data # Check for a specific string in your index.html

@patch('your_wedding_app.qr_generator.generate_qr_code_image')
def test_register_guest_success(mock_generate_qr, client, db_session): # Add db_session to access test DB directly
    # Ensure the guest list is empty before the test
    assert db_session.query(Guest).count() == 0

    response = client.post('/register_guest', data={
        'name': 'Test Register Guest',
        'phone': '1234567890',
        'card_type': 'single'
    }, follow_redirects=True)

    assert response.status_code == 200 # Should redirect to index page after success
    assert b"Guest registered and QR code generated successfully!" in response.data # Check for flash message
    assert db_session.query(Guest).count() == 1

    guest = db_session.query(Guest).filter_by(phone="1234567890").first()
    assert guest.name == "Test Register Guest"
    assert guest.card_type == "single"
    assert guest.qr_code_id is not None
    assert guest.qr_code_url is not None # Should be set after QR generation and save

    mock_generate_qr.assert_called_once()
    # You can assert the arguments of mock_generate_qr if you want to be very specific
    # mock_generate_qr.assert_called_once_with(guest.qr_code_id, os.path.join(client.application.root_path, 'static/qrcodes', f'{guest.qr_code_id}.png'))


@patch('your_wedding_app.qr_generator.generate_qr_code_image')
def test_register_guest_duplicate_phone(mock_generate_qr, client, db_session):
    # Create a guest first
    guest = Guest(name="Existing", phone="9876543210", qr_code_id="existing_qr_id")
    db_session.add(guest)
    db_session.commit()
    assert db_session.query(Guest).count() == 1

    response = client.post('/register_guest', data={
        'name': 'Duplicate Guest',
        'phone': '9876543210', # Duplicate phone
        'card_type': 'single'
    }, follow_redirects=True)

    assert response.status_code == 200 # Should redirect back to registration form
    assert b"This phone number is already registered!" in response.data # Check for flash message
    assert db_session.query(Guest).count() == 1 # Still only one guest

    mock_generate_qr.assert_not_called() # QR generation should not happen for duplicate


def test_register_guest_get_request(client):
    response = client.get('/register_guest')
    assert response.status_code == 200
    assert b"Guest Registration Form" in response.data # Check for content on your registration page

# Test /scan_qr route
def test_scan_qr_get_request(client):
    response = client.get('/scan_qr')
    assert response.status_code == 200
    assert b"Scan QR Code" in response.data # Check for content on your scan_qr_form.html


def test_scan_qr_post_guest_found_first_entry(client, db_session):
    # Arrange: Add a guest who hasn't entered yet
    qr_id = "test_qr_123"
    guest = Guest(name="Scanned Guest", phone="1231231231", qr_code_id=qr_id, has_entered=False)
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)

    response = client.post('/scan_qr', data={'qr_id': qr_id}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome Scanned Guest! Entry recorded." in response.data
    
    # Verify guest's status in DB
    updated_guest = db_session.query(Guest).filter_by(qr_code_id=qr_id).first()
    assert updated_guest.has_entered is True
    assert updated_guest.entry_time is not None


def test_scan_qr_post_guest_found_already_entered(client, db_session):
    # Arrange: Add a guest who has already entered
    qr_id = "test_qr_456"
    entry_time = datetime(2025, 7, 10, 10, 0, 0) # Fixed entry time for predictability
    guest = Guest(name="Entered Guest", phone="4564564564", qr_code_id=qr_id, has_entered=True, entry_time=entry_time)
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)

    response = client.post('/scan_qr', data={'qr_id': qr_id}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Entered Guest has already entered" in response.data
    assert b"at 2025-07-10 10:00:00" in response.data # Check exact time if displayed

    # Verify guest's status in DB (should not change)
    updated_guest = db_session.query(Guest).filter_by(qr_code_id=qr_id).first()
    assert updated_guest.has_entered is True
    assert updated_guest.entry_time == entry_time # Time should not be updated


def test_scan_qr_post_guest_not_found(client, db_session):
    response = client.post('/scan_qr', data={'qr_id': "non_existent_qr"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"QR Code not recognized." in response.data

def test_scan_qr_post_no_qr_id_provided(client, db_session):
    response = client.post('/scan_qr', data={'qr_id': ""}, follow_redirects=True) # Empty QR ID

    assert response.status_code == 200
    assert b"No QR ID provided." in response.data