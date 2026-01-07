# app/db/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from .env
load_dotenv()

# Get DATABASE_URL from .env, fallback to SQLite if not set
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db"  # Fallback untuk development lokal
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # Hapus connect_args check_same_thread karena itu hanya untuk SQLite
    **({"pool_pre_ping": True} if "postgresql" in SQLALCHEMY_DATABASE_URL else {"connect_args": {"check_same_thread": False}})
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

