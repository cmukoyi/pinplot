from sqlalchemy import create_engine
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
    """Initialize database — creates any missing tables.

    Uses SQLAlchemy's checkfirst=True (default in create_all) so existing
    tables are never dropped or modified; only genuinely new tables are added.
    """
    Base.metadata.create_all(bind=engine)
