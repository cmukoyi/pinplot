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
    """Initialize database tables - only creates tables that don't already exist."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if existing_tables:
        print(f"Database has {len(existing_tables)} existing tables. Checking for new tables...")
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            print(f"Creating table: {table.name}")
            table.create(bind=engine)
    print("Database initialization complete.")
