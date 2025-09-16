from __future__ import annotations
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///commission.db")
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="consultant")
    created_at = Column(DateTime, default=datetime.utcnow)
    invoices = relationship("Invoice", back_populates="consultant")

class Rule(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True)
    consultant_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    client = Column(String(255), nullable=True)
    service_type = Column(String(255), nullable=True)
    rate = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(100), nullable=False)
    date = Column(Date, nullable=False)
    client = Column(String(255), nullable=False)
    service_type = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    paid = Column(Boolean, default=False)
    consultant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    commission_rate = Column(Float, default=0.0)
    commission_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    consultant = relationship("User", back_populates="invoices")
    __table_args__ = (UniqueConstraint('invoice_number', name='uq_invoice_number'),)

def init_db():
    Base.metadata.create_all(bind=engine)
