"""
database.py
-------------
Yeh file PostgreSQL se connection banati hai.
SQLAlchemy ka use kar rahe hain — yeh ek "ORM" hai, matlab
hum Python classes likhenge aur woh automatically SQL tables ban jaayengi.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# .env file se environment variables load karo
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL .env file mein nahi mili! .env.example ko .env mein copy karo aur apni details daalo.")

# Engine = database ke saath connection ka "pipe"
engine = create_engine(DATABASE_URL)

# SessionLocal = har request ke liye ek temporary database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = saari models (tables) isse inherit karengi
Base = declarative_base()


def get_db():
    """
    Yeh function har API request ke liye ek database session deta hai,
    aur request khatam hone ke baad usse band kar deta hai.
    FastAPI mein yeh "dependency injection" ke tarike se use hota hai.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
