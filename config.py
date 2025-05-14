import os

# Option 1: Use environment variable (recommended for Render.com)
DATABASE_URL = os.environ.get("DATABASE_URL")
if os.environ.get("ENV") == "test":
    DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")
