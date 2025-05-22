# models.py
import os
from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv

# --- THESE TWO LINES MUST BE HERE AND AT THE TOP ---
load_dotenv()
load_dotenv(".env.local", override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # This will now correctly raise an error if DATABASE_URL is not found *after* loading dotenv
    raise ValueError("DATABASE_URL environment variable is not set after loading .env files.")

engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()

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
    card_type = Column(String, default="single", nullable=False) # e.g., "single" or "double"

    def __repr__(self):
        return f"<Guest(name='{self.name}', phone='{self.phone}', card_type='{self.card_type}')>"