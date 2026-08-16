import argparse
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.repositories import user_repository


def promote_admin(username: str) -> None:
    db = SessionLocal()
    try:
        user = user_repository.find_by_username(db, username)
        if user is None:
            raise ValueError(f"User not found: {username}")
        user_repository.update_role(db, user, "ADMIN")
        db.commit()
        print(f"Promoted {username} to ADMIN")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a user to ADMIN")
    parser.add_argument("username", help="Username to promote")
    args = parser.parse_args()

    try:
        promote_admin(args.username)
    except ValueError as error:
        parser.exit(status=1, message=f"Error: {error}\n")


if __name__ == "__main__":
    main()
