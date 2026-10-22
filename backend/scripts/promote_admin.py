
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User


def main() -> int:
    admin_email = settings.ADMIN_EMAIL.strip().lower()

    if not admin_email:
        print("ERROR: Set ADMIN_EMAIL in the backend environment first.")
        return 1

    if SessionLocal is None:
        print("ERROR: DATABASE_URL is not configured.")
        return 1

    db = SessionLocal()

    try:
        user = db.scalar(
            select(User).where(User.email == admin_email)
        )

        if user is None:
            print(
                "ERROR: No registered user matches ADMIN_EMAIL. "
                "Register that account first, then rerun this script."
            )
            return 1

        if user.is_admin:
            print(f"Account {admin_email} is already an administrator.")
            return 0

        user.is_admin = True
        db.commit()

        print(f"Administrator privileges granted to {admin_email}.")
        return 0

    except Exception as exc:
        db.rollback()
        print(f"ERROR: Admin promotion failed: {exc}")
        return 1

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
