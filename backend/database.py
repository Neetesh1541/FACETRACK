
import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from .env file")

# Create database engine
engine = create_engine(DATABASE_URL)

# Create database session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Test database connection
try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))

        print("FACETRACK DATABASE CONNECTED SUCCESSFULLY!")
        print("Test Result:", result.scalar())

except Exception as error:
    print("DATABASE CONNECTION FAILED!")
    print(error)
