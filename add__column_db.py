from app_web import db
db.engine.execute('ALTER TABLE guests ADD COLUMN guest_type TEXT')
