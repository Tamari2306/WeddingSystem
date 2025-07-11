# models.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
from contextlib import contextmanager # <--- ADD THIS LINE

Base = declarative_base()

# Configure the engine (use a default for dev/prod, can be overridden for test)
_engine = None # Will be set by app_web or test config
_SessionLocal = None # Will be set by app_web or test config

def init_db(app_or_db_uri):
    global _engine, _SessionLocal
    if isinstance(app_or_db_uri, str): # Passed a URI string
        _engine = create_engine(app_or_db_uri)
    else: # Assume Flask app object
        _engine = create_engine(app_or_db_uri.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///site.db'))

    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

@contextmanager # <--- ADD THIS DECORATOR
def get_db_session():
    """Returns a new database session."""
    if _SessionLocal is None:
        raise Exception("Database not initialized. Call init_db() first.")
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close() # Ensure session is closed after use

class Guest(Base):
    __tablename__ = 'guests'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    qr_code_id = Column(String, unique=True, nullable=False)
    qr_code_url = Column(String, nullable=True) # URL to the generated QR code image
    has_entered = Column(Boolean, default=False)
    entry_time = Column(DateTime, nullable=True)
    visual_id = Column(Integer, unique=True, nullable=True) # New visual ID
    card_type = Column(String, default='single', nullable=False) # 'single' or 'double'

    def __repr__(self):
        return f"<Guest(id={self.id}, name='{self.name}', phone='{self.phone}', qr_code_id='{self.qr_code_id}')>"

    def save(self, session):
        session.add(self)
        session.commit()

    def delete(self, session):
        session.delete(self)
        session.commit()

# Example usage with `get_db_session` context manager
def create_guest(name, phone, qr_code_id, qr_code_url=None, visual_id=None, card_type='single'):
    with get_db_session() as session:
        guest = Guest(name=name, phone=phone, qr_code_id=qr_code_id,
                      qr_code_url=qr_code_url, visual_id=visual_id, card_type=card_type)
        session.add(guest)
        session.commit()
        session.refresh(guest)
        return guest

def get_guest_by_qr_code_id(qr_code_id):
    with get_db_session() as session:
        return session.query(Guest).filter_by(qr_code_id=qr_code_id).first()