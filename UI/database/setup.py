import os
from contextlib import contextmanager
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# 1. Pull the connection string from environment variables for security/flexibility.
# Default to a local SQLite database if no environment variable is provided.
# 🔌 Load the environment variables from your .env file
load_dotenv()

# 📥 Fetch credentials with clean fallback defaults
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "portfolio_db")
PAYCHECK_DB_NAME = os.getenv("PAYCHECK_DB_NAME", "paycheck_db")

# 🛡️ Safety Check: URL-encode the password in case it contains characters like '@', ':', or '!'
safe_password = quote_plus(DB_PASSWORD)

# 🏗️ Dynamically construct the connection string
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
PAYCHECK_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{PAYCHECK_DB_NAME}"

# 2. Initialize the Engine
# Note: 'check_same_thread=False' is strictly required for SQLite when running 
# inside multi-threaded frameworks like Streamlit or Fastapi. Remove it for PostgreSQL/MySQL.
is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if is_sqlite else {}
)
paycheck_engine = create_engine(
    PAYCHECK_DATABASE_URL, 
    connect_args={"check_same_thread": False} if is_sqlite else {}
)
# 3. Create a configured Session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
PaycheckSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=paycheck_engine)

# 4. The Universal Context Manager
@contextmanager
def get_db():
    """
    Safely provisions a database session and guarantees closure 
    even if an unexpected application exception or crash occurs.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()  # Automatically commit transactions if the block finishes successfully
    except Exception:
        session.rollback() # Automatically roll back modifications if an error happens
        raise
    finally:
        session.close()    # Always release the connection back to the pool

@contextmanager
def get_paycheck_db():
    """
    Safely provisions a database session and guarantees closure 
    even if an unexpected application exception or crash occurs.
    """
    session = PaycheckSessionLocal()
    try:
        yield session
        session.commit()  # Automatically commit transactions if the block finishes successfully
    except Exception:
        session.rollback() # Automatically roll back modifications if an error happens
        raise
    finally:
        session.close()    # Always release the connection back to the pool