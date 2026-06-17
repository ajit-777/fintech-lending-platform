"""Run: python create_admin.py"""
import sys
from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password

db = SessionLocal()

email = sys.argv[1] if len(sys.argv) > 1 else "admin@lender.com"
phone = sys.argv[2] if len(sys.argv) > 2 else "+919999999999"
password = sys.argv[3] if len(sys.argv) > 3 else "Admin@1234"

existing = db.query(User).filter(User.email == email).first()
if existing:
    existing.role = "admin"
    db.commit()
    print(f"Updated existing user {email} → role=admin")
else:
    user = User(email=email, phone=phone, password_hash=hash_password(password), role="admin")
    db.add(user)
    db.commit()
    print(f"Created admin user: {email} / {password}")

db.close()
