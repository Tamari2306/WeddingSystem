from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime

Base = declarative_base()
engine = create_engine('sqlite:///guests.db')
SessionLocal = sessionmaker(bind=engine)

class Guest(Base):
    __tablename__ = 'guests'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    qr_code_id = Column(String, unique=True, nullable=False)
    qr_code_url = Column(String, nullable=False)
    has_entered = Column(Boolean, default=False)
    entry_time = Column(DateTime, default=None)
    visual_id = Column(Integer, nullable=False)  # Required for sorting and visual order

    def __repr__(self):
        return f"<Guest(name='{self.name}', phone='{self.phone}', qr_code_id='{self.qr_code_id}')>"
