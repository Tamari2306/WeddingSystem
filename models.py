import os
from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from dotenv import load_dotenv


load_dotenv()

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///guests.db")
engine = create_engine(DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(bind=engine))

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