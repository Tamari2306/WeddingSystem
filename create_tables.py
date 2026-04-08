import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from models import Base, Guest, engine
import traceback

print("--- THIS IS THE CORRECT create_tables.py FILE RUNNING ---")

if __name__ == "__main__":
    # Ensure .env.local is loaded without overriding for development
    load_dotenv() # Load .env first
    load_dotenv(".env.local", override=True) # Then load .env.local to override
    print("Loaded .env.local for database operations.")

    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable is not set after loading .env files.")
        exit(1)

    print(f"Attempting to connect to: {DATABASE_URL}")

    try:
        # Base.metadata.create_all(engine) creates the tables defined in your models
        Base.metadata.create_all(engine)
        print("Database tables created successfully using SQLAlchemy metadata.")

        # Optional: Add a simple query test here (if you want, but app_web.py will test it)
        # from sqlalchemy.orm import sessionmaker, scoped_session
        # SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
        # session = SessionLocal()
        # guest_count = session.query(Guest).count()
        # print(f"Test query successful. Found {guest_count} guests.")
        # session.close()


    except Exception as e:
        print(f"An error occurred during database table creation or connection test: {e}")
        import traceback
    traceback.print_exc()

print("Script finished. Check your database for the 'guests' table.")