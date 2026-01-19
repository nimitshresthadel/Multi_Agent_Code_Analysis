"""
Database setup script - creates initial admin user
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.core.security import get_password_hash
import uuid


def create_admin_user():
    """Create initial admin user."""
    db = SessionLocal()

    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()

        if existing_admin:
            print(f"✓ Admin user already exists: {existing_admin.email}")
            return

        # Create admin user
        admin = User(
            id=str(uuid.uuid4()),
            email="admin@codeanalysis.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),  # Change this!
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_active=True
        )

        db.add(admin)
        db.commit()

        print("✓ Admin user created successfully!")
        print(f"  Email: {admin.email}")
        print(f"  Username: {admin.username}")
        print(f"  Password: admin123")
        print("\n⚠️  Please change the admin password after first login!")

    except Exception as e:
        print(f"✗ Error creating admin user: {str(e)}")
        db.rollback()
    finally:
        db.close()


def create_test_users():
    """Create test users for development."""
    db = SessionLocal()

    try:
        test_users = [
            {
                "email": "user1@test.com",
                "username": "testuser1",
                "password": "password123",
                "full_name": "Test User One",
                "role": UserRole.USER
            },
            {
                "email": "user2@test.com",
                "username": "testuser2",
                "password": "password123",
                "full_name": "Test User Two",
                "role": UserRole.USER
            }
        ]

        created_count = 0
        for user_data in test_users:
            # Check if user exists
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if existing:
                print(f"  User {user_data['email']} already exists, skipping...")
                continue

            user = User(
                id=str(uuid.uuid4()),
                email=user_data["email"],
                username=user_data["username"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=True
            )

            db.add(user)
            created_count += 1

        if created_count > 0:
            db.commit()
            print(f"✓ Created {created_count} test users")
        else:
            print("  All test users already exist")

    except Exception as e:
        print(f"✗ Error creating test users: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 50)
    print("Database Setup Script")
    print("=" * 50)

    print("\n1. Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created")

    print("\n2. Creating admin user...")
    create_admin_user()

    print("\n3. Creating test users...")
    create_test_users()

    print("\n" + "=" * 50)
    print("Setup complete!")
    print("=" * 50)
