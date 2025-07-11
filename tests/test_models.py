import pytest
from models import Guest, Base, get_db_session # Import get_db_session
from sqlalchemy import create_engine
from datetime import datetime
import uuid

# Re-using the db_session fixture from conftest.py
# If you want more granular control, you could define a similar fixture here
# but it's cleaner to rely on the conftest.py fixture.

def test_guest_creation(db_session):
    guest = Guest(name="Alice", phone="1234567890", qr_code_id=str(uuid.uuid4()))
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest) # Get the ID assigned by the database

    assert guest.id is not None
    assert guest.name == "Alice"
    assert db_session.query(Guest).count() == 1

def test_guest_update_entry_status(db_session):
    guest = Guest(name="Bob", phone="0987654321", qr_code_id=str(uuid.uuid4()), has_entered=False)
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)

    guest.has_entered = True
    guest.entry_time = datetime.now()
    db_session.commit()
    db_session.refresh(guest)

    updated_guest = db_session.query(Guest).filter_by(phone="0987654321").first()
    assert updated_guest.has_entered is True
    assert updated_guest.entry_time is not None

def test_guest_delete(db_session):
    guest = Guest(name="Charlie", phone="1112223334", qr_code_id=str(uuid.uuid4()))
    db_session.add(guest)
    db_session.commit()
    db_session.refresh(guest)
    assert db_session.query(Guest).count() == 1

    db_session.delete(guest)
    db_session.commit()
    assert db_session.query(Guest).count() == 0

def test_guest_unique_phone_constraint(db_session):
    qr_id1 = str(uuid.uuid4())
    guest1 = Guest(name="Dave", phone="5551234567", qr_code_id=qr_id1)
    db_session.add(guest1)
    db_session.commit()

    qr_id2 = str(uuid.uuid4())
    guest2 = Guest(name="David", phone="5551234567", qr_code_id=qr_id2)
    db_session.add(guest2)
    
    with pytest.raises(Exception): # SQLAlchemy will raise an IntegrityError
        db_session.commit()
    db_session.rollback() # Rollback the session after the failed commit
    assert db_session.query(Guest).count() == 1 # Only guest1 should be there

def test_guest_unique_qr_code_id_constraint(db_session):
    common_qr_id = str(uuid.uuid4())
    guest1 = Guest(name="Eve", phone="9998887777", qr_code_id=common_qr_id)
    db_session.add(guest1)
    db_session.commit()

    guest2 = Guest(name="Eve Duplicate", phone="6665554444", qr_code_id=common_qr_id)
    db_session.add(guest2)

    with pytest.raises(Exception): # SQLAlchemy will raise an IntegrityError
        db_session.commit()
    db_session.rollback()
    assert db_session.query(Guest).count() == 1