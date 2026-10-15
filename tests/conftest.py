import pytest


@pytest.fixture
def signed_in():
    """Every /api route requires a signed-in user; run the test as an admin."""
    from server.backend_api import app
    from server.auth import User, get_current_user

    app.dependency_overrides[get_current_user] = lambda: User(username="test_admin", role="admin")
    yield
    app.dependency_overrides.pop(get_current_user, None)
