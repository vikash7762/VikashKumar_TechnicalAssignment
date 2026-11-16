
from getpass import getpass

from app.database import SessionLocal
from app.models import User
from app.auth import hash_password


def create_admin():
    db = SessionLocal()

    try:
        name = input("Enter admin name: ").strip()
        email = input("Enter admin email: ").strip().lower()
        password = getpass("Enter admin password: ")
        confirm_password = getpass("Confirm admin password: ")

        if not name or not email or not password:
            print("Error: All fields are required.")
            return

        if password != confirm_password:
            print("Error: Passwords do not match.")
            return

        if len(password) < 8:
            print("Error: Password must be at least 8 characters.")
            return

        existing_user = db.query(User).filter(
            User.email == email
        ).first()

        if existing_user:
            print("Error: This email is already registered.")
            return

        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True
        )

        db.add(admin)
        db.commit()

        print("\nAdmin account created successfully!")

    except Exception as error:
        db.rollback()
        print("Error creating admin:", error)

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
