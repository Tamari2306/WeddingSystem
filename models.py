# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

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

