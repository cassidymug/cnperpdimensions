import pytest
from app.models.user import User
from app.models.role import Role

@pytest.mark.unit
@pytest.mark.models
def test_user_creation(db_session):
    """Test that a user can be created and retrieved from the database"""
    # Create a test user
    user = User(
        username="testuser1",
        email="testuser1@example.com",
        hashed_password="hashed_password",
        active=True,
        first_name="Test",
        last_name="User 1"
    )
    db_session.add(user)
    db_session.commit()
    
    # Retrieve the user from the database
    retrieved_user = db_session.query(User).filter_by(username="testuser1").first()
    
    # Assert that the user was created correctly
    assert retrieved_user is not None
    assert retrieved_user.username == "testuser1"
    assert retrieved_user.email == "testuser1@example.com"
    assert retrieved_user.active is True
    assert retrieved_user.first_name == "Test"
    assert retrieved_user.last_name == "User 1"

@pytest.mark.unit
@pytest.mark.models
def test_user_role_relationship(db_session):
    """Test that roles can be assigned to users"""
    # Create a role
    role = Role(name="test_role", description="Test Role")
    db_session.add(role)
    db_session.flush()
    
    # Create a user and assign the role
    user = User(
        username="roleuser",
        email="roleuser@example.com",
        hashed_password="hashed_password",
        active=True,
        first_name="Role",
        last_name="User"
    )
    user.role_obj = role
    db_session.add(user)
    db_session.commit()
    
    # Retrieve the user and check the role
    retrieved_user = db_session.query(User).filter_by(username="roleuser").first()
    assert retrieved_user is not None
    assert retrieved_user.role_obj is not None
    assert retrieved_user.role_obj.name == "test_role"