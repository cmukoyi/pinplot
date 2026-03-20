from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://beacon_user:beacon_password@db:5432/beacon_telematics")

# PostgreSQL engine configuration
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables - always runs create_all (idempotent, only creates missing tables)"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    if existing_tables:
        print(f"Database has {len(existing_tables)} existing tables. Running create_all to add any missing tables.")
    # create_all is safe to call even when tables exist — it only creates missing ones
    Base.metadata.create_all(bind=engine)
