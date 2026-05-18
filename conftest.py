import os

import pytest
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "salt_tracker.settings")


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="tester",
        password="test-password-123",
    )
