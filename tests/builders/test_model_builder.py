import pytest

from sqlalchemy_continuum.builder import prevent_reentry
from tests import TestCase


def test_prevent_reentry_resets_after_exception():
    calls = []

    @prevent_reentry
    def handler():
        calls.append(None)
        raise ValueError

    for _ in range(2):
        with pytest.raises(ValueError):
            handler()
    assert len(calls) == 2


class TestVersionModelBuilder(TestCase):
    def test_builds_relationship(self):
        assert self.Article.versions

    def test_parent_has_access_to_versioning_manager(self):
        assert self.Article.__versioning_manager__
