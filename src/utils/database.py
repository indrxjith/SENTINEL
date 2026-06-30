"""
Database connection module for the SENTINEL project.

This module:
- Loads database settings from database.yaml
- Loads the database password from .env
- Creates a SQLAlchemy engine
- Tests the PostgreSQL connection
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from src.utils.config import load_config


# ---------------------------------------------------------------------
# Load Environment Variables
# ---------------------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------------------
# Load Database Configuration
# ---------------------------------------------------------------------

db_config = load_config("database.yaml")["database"]

host = db_config["host"]
port = db_config["port"]
database = db_config["name"]
user = db_config["user"]
password = os.getenv("DB_PASSWORD")

if password is None:
    raise ValueError(
        "DB_PASSWORD was not found. Please check your .env file."
    )


# ---------------------------------------------------------------------
# Build Database URL
# ---------------------------------------------------------------------

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=user,
    password=password,
    host=host,
    port=port,
    database=database,
)


# ---------------------------------------------------------------------
# Create SQLAlchemy Engine
# ---------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


# ---------------------------------------------------------------------
# Test Connection
# ---------------------------------------------------------------------

def test_connection():
    """
    Test the PostgreSQL database connection.
    """

    try:
        with engine.connect() as connection:

            version = connection.execute(
                text("SELECT version();")
            ).scalar()

            print("\n✅ Connected to PostgreSQL successfully!\n")
            print(version)

    except Exception as error:

        print("\n❌ Database connection failed!\n")
        print(error)


# ---------------------------------------------------------------------
# Run Directly
# ---------------------------------------------------------------------

if __name__ == "__main__":
    test_connection()