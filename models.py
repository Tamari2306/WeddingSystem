# models.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from contextlib import contextmanager

Base = declarative_base()

# Engine & Session placeholders (set by init_db)
_engine = None
_SessionLocal = None

def init_db(app_or_db_uri):
    """
    Initialize the engine and sessionmaker.
    Accepts either a Flask app object or a DB URI string.
    """
    global _engine, _SessionLocal
    if isinstance(app_or_db_uri, str):
        uri = app_or_db_uri
    else:
        # Flask app passed
        uri = app_or_db_uri.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///site.db')

    _engine = create_engine(uri, connect_args={"check_same_thread": False} if uri.startswith("sqlite") else {})
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(_engine)

@contextmanager
def get_db_session():
    if _SessionLocal is None:
        raise Exception("Database not initialized. Call init_db(app) first.")
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()

class Guest(Base):
    __tablename__ = 'guests'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, default="")
    phone = Column(String, nullable=False, default="")   # not unique: allow same phone for family if needed
    qr_code_id = Column(String, unique=True, nullable=False)
    qr_code_url = Column(String, nullable=True)
    has_entered = Column(Boolean, default=False)
    entry_time = Column(DateTime, nullable=True)
    visual_id = Column(Integer, unique=True, nullable=True)
    card_type = Column(String, default='single', nullable=False)  # stored as 'single'/'double'/'family'
    group_size = Column(Integer, default=1)        # total allowed entries for this card
    checked_in_count = Column(Integer, default=0) # how many entries used so far

    def __repr__(self):
        return f"<Guest(id={self.id}, visual_id={self.visual_id}, name='{self.name}', phone='{self.phone}', card_type='{self.card_type}', group_size={self.group_size}, checked_in={self.checked_in_count})>"

    # convenience helpers that use an external session
    def save(self, session):
        session.add(self)
        session.commit()
        session.refresh(self)

    def delete(self, session):
        session.delete(self)
        session.commit()

# helper convenience (not used everywhere)
def create_guest(session, **kwargs):
    guest = Guest(**kwargs)
    session.add(guest)
    session.commit()
    session.refresh(guest)
    return guest
