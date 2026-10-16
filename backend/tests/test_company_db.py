import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.company import Company


def test_company_database_connection():
    assert SessionLocal is not None

    db = SessionLocal()

    try:
        company = Company(
            name="JobShield Test Company",
            legal_name="JobShield Test Company Private Limited",
            description="Temporary database test record.",
            website="https://example.com",
        )

        db.add(company)
        db.commit()
        db.refresh(company)

        assert company.id is not None
        assert company.name == "JobShield Test Company"

        result = db.execute(
            select(Company).where(
                Company.id == company.id
            )
        )

        saved_company = result.scalar_one()

        assert saved_company.name == "JobShield Test Company"

        db.delete(saved_company)
        db.commit()

    finally:
        db.close()