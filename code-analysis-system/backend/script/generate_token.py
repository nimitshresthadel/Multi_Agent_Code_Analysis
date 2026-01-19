"""
Generate authentication token for testing
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.user import User
from app.core.security import create_access_token
from datetime import timedelta


def generate_token(email: str):
    """Generate JWT token for a user."""
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            print(f"✗ User with email '{email}' not found")
            return

        # Create token
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role.value},
            expires_delta=timedelta(days=7)  # 7 days for testing
        )

        print(f"✓ Token generated for {user.email}")
        print(f"\nUser Details:")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Username: {user.username}")
        print(f"  Role: {user.role.value}")
        print(f"\nAccess Token (valid for 7 days):")
        print(f"{access_token}")
        print(f"\nUse in API requests:")
        print(f'Authorization: Bearer {access_token}')

    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Generate JWT token for a user')
    parser.add_argument('email', help='User email address')

    args = parser.parse_args()
    generate_token(args.email)
