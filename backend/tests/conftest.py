"""
Test configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.company import Company

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_company(db_session):
    """Create a test company."""
    company = Company(
        name="Test Company",
        domain="test.com",
        is_active=True
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def super_admin(db_session):
    """Create a super admin user."""
    user = User(
        email="superadmin@test.com",
        password_hash=get_password_hash("SuperAdmin123!"),
        first_name="Super",
        last_name="Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session, test_company):
    """Create an admin user."""
    user = User(
        email="admin@test.com",
        password_hash=get_password_hash("Admin123!"),
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        company_id=test_company.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session, test_company):
    """Create a regular user."""
    user = User(
        email="user@test.com",
        password_hash=get_password_hash("User123!"),
        first_name="Regular",
        last_name="User",
        role=UserRole.USER,
        company_id=test_company.id,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(client, admin_user):
    """Get authentication token for admin user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin123!"}
    )
    return response.json()["access_token"]


@pytest.fixture
def super_admin_token(client, super_admin):
    """Get authentication token for super admin."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@test.com", "password": "SuperAdmin123!"}
    )
    return response.json()["access_token"]
