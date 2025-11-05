import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.role import Role, Permission
from app.core.security import create_access_token

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_engine():
    """Create a SQLite in-memory database engine for testing"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a new database session for a test"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with a database session dependency override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db_session):
    """Create a test user for authentication tests"""
    # Create test role and permissions
    role = Role(name="test_role", description="Role for testing")
    db_session.add(role)
    db_session.flush()
    
    # Create test permission
    permission = Permission(
        name="test.permission",
        description="Test permission",
        module="test",
        action="test",
        resource="all"
    )
    db_session.add(permission)
    db_session.flush()
    
    # Associate permission with role
    role.permissions.append(permission)
    
    # Create test user
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        is_active=True,
        full_name="Test User"
    )
    user.roles.append(role)
    db_session.add(user)
    db_session.commit()
    
    return user

@pytest.fixture(scope="function")
def auth_headers(test_user):
    """Create authentication headers with JWT token"""
    access_token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {access_token}"}