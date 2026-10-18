
import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.report import ReportCreate
from app.schemas.company import CompanyCreate
from app.schemas.email import EmailCreate
from app.schemas.job import JobCreate
from app.schemas.message import MessageCreate
from app.schemas.phone_number import PhoneNumberCreate
from app.schemas.recruiter import RecruiterCreate
from app.schemas.website import WebsiteCreate


# Authentication validation

def test_register_rejects_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="not-an-email",
            password="StrongPassword123!",
        )


def test_register_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="person@example.com",
            password="short",
        )


def test_register_rejects_password_over_maximum_length():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="person@example.com",
            password="P" * 129,
        )


def test_login_rejects_empty_password():
    with pytest.raises(ValidationError):
        LoginRequest(
            email="person@example.com",
            password="",
        )


# Report validation

def test_report_rejects_empty_required_fields():
    for field in ("report_type", "target_value", "description"):
        data = {
            "report_type": "website",
            "target_value": "example.com",
            "description": "A report",
        }
        data[field] = ""

        with pytest.raises(ValidationError):
            ReportCreate(**data)


def test_report_rejects_report_type_over_maximum_length():
    with pytest.raises(ValidationError):
        ReportCreate(
            report_type="x" * 51,
            target_value="example.com",
            description="A report",
        )


def test_report_rejects_target_over_maximum_length():
    with pytest.raises(ValidationError):
        ReportCreate(
            report_type="website",
            target_value="x" * 1001,
            description="A report",
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("report_type", "   "),
        ("target_value", "   "),
        ("description", "   "),
    ],
)
def test_report_rejects_whitespace_only_required_fields(field, value):
    data = {
        "report_type": "website",
        "target_value": "example.com",
        "description": "A report",
    }
    data[field] = value

    with pytest.raises(ValidationError):
        ReportCreate(**data)


# Company validation

def test_company_rejects_blank_name():
    with pytest.raises(ValidationError):
        CompanyCreate(name="   ")


def test_company_rejects_name_over_database_limit():
    with pytest.raises(ValidationError):
        CompanyCreate(name="C" * 256)


def test_company_allows_optional_fields_to_be_none():
    company = CompanyCreate(
        name="Example Company",
        legal_name=None,
        description=None,
        website=None,
    )
    assert company.website is None


# Email validation

def test_email_rejects_invalid_email_address():
    with pytest.raises(ValidationError):
        EmailCreate(email_address="not-an-email")


def test_email_rejects_email_over_database_limit():
    with pytest.raises(ValidationError):
        EmailCreate(email_address="a" * 321)


def test_email_allows_optional_description_to_be_none():
    assert EmailCreate(
        email_address="person@example.com",
        description=None,
    ).description is None


# Job validation

def test_job_rejects_blank_url():
    with pytest.raises(ValidationError):
        JobCreate(job_url="   ")


def test_job_rejects_invalid_url():
    with pytest.raises(ValidationError):
        JobCreate(job_url="not-a-url")


def test_job_rejects_url_over_database_limit():
    with pytest.raises(ValidationError):
        JobCreate(job_url="https://example.com/" + "a" * 2000)


def test_job_allows_optional_fields_to_be_none():
    job = JobCreate(
        job_url="https://example.com/jobs/1",
        title=None,
        company_name=None,
        description=None,
    )
    assert job.title is None


# Message validation

def test_message_rejects_blank_text():
    with pytest.raises(ValidationError):
        MessageCreate(message_text="   ")


def test_message_accepts_nonblank_text():
    message = MessageCreate(message_text="Please verify this job offer.")
    assert message.message_text == "Please verify this job offer."


# Phone number validation

def test_phone_number_rejects_blank_value():
    with pytest.raises(ValidationError):
        PhoneNumberCreate(phone_number="   ")


def test_phone_number_rejects_value_over_database_limit():
    with pytest.raises(ValidationError):
        PhoneNumberCreate(phone_number="1" * 51)


def test_phone_number_accepts_common_formatting():
    phone = PhoneNumberCreate(phone_number="+1 (555) 123-4567")
    assert phone.phone_number == "+1 (555) 123-4567"


def test_phone_number_allows_optional_fields_to_be_none():
    phone = PhoneNumberCreate(
        phone_number="+1 (555) 123-4567",
        country_code=None,
        description=None,
    )
    assert phone.country_code is None


# Recruiter validation

def test_recruiter_rejects_blank_name():
    with pytest.raises(ValidationError):
        RecruiterCreate(name="   ")


def test_recruiter_rejects_invalid_optional_email():
    with pytest.raises(ValidationError):
        RecruiterCreate(
            name="Example Recruiter",
            email="not-an-email",
        )


def test_recruiter_rejects_invalid_profile_url():
    with pytest.raises(ValidationError):
        RecruiterCreate(
            name="Example Recruiter",
            profile_url="not-a-url",
        )


def test_recruiter_allows_optional_fields_to_be_none():
    recruiter = RecruiterCreate(
        name="Example Recruiter",
        email=None,
        phone=None,
        company_name=None,
        profile_url=None,
        description=None,
    )
    assert recruiter.email is None


# Website validation

def test_website_rejects_blank_url():
    with pytest.raises(ValidationError):
        WebsiteCreate(website_url="   ")


def test_website_rejects_invalid_url():
    with pytest.raises(ValidationError):
        WebsiteCreate(website_url="not-a-url")


def test_website_rejects_url_over_database_limit():
    with pytest.raises(ValidationError):
        WebsiteCreate(website_url="https://example.com/" + "a" * 1000)


def test_website_allows_optional_fields_to_be_none():
    website = WebsiteCreate(
        website_url="https://example.com",
        domain=None,
        description=None,
    )
    assert website.domain is None
