
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.company import Company

from app.models.user import User  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.risk_score import RiskScore  # noqa: F401
from app.models.risk_signal import RiskSignal  # noqa: F401

def test_company_database_connection():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    try:
        Base.metadata.create_all(bind=test_engine)

        with TestSessionLocal() as db:
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

    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
