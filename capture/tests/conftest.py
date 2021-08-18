import pytest

from capture.utils import ctx as _ctx


@pytest.fixture
def ctx():
    yield _ctx
