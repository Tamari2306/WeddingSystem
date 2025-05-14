import os
from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

# --- Database Connection using DATABASE_URL ---
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    # Handle the case where DATABASE_URL might not be set (e.g., local development)
    # You might want to provide a fallback or raise an error.
    print("Warning: DATABASE_URL environment variable not found.")
    engine = None  # Or raise an exception

SessionLocal = sessionmaker(bind=engine) if engine else None

# --- Models ---
class Guest(Base):
    __tablename__ = "guests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    qr_code_id = Column(String, unique=True, nullable=False)
    qr_code_url = Column(String, nullable=False)
    has_entered = Column(Boolean, default=False)
    entry_time = Column(DateTime, default=None)
    visual_id = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<Guest(name='{self.name}', phone='{self.phone}', qr_code_id='{self.qr_code_id}')>"