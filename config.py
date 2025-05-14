import os

# Option 1: Use environment variable (recommended for Render.com)
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Option 2: Fallback to a default PostgreSQL connection string (less ideal for Render)
    #  DATABASE_URL = "postgresql://user:password@host:port/database_name"
    #  Replace with your actual PostgreSQL credentials if you use this.
    DATABASE_URL = None #  It's best to force the user to set the environment variable.

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not set.  "
                         "You must set it as an environment variable or in config.py")
