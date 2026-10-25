import sqlalchemy as sa

from sqlalchemy_continuum import is_session_modified, utils
from tests import TestCase


class TestIsSessionModified(TestCase):
    def setup_method(self, method):
        super().setup_method(method)
        self.session.add_all([self.Article(name=f'Article {i}') for i in range(3)])
        self.session.commit()
        self.articles = self.session.scalars(sa.select(self.Article)).all()

    def test_clean_session(self):
        assert not is_session_modified(self.session)

    def test_new_object(self):
        self.session.add(self.Article(name='New article'))
        assert is_session_modified(self.session)

    def test_modified_object(self):
        self.articles[1].name = 'Updated name'
        assert is_session_modified(self.session)

    def test_deleted_object(self):
        self.session.delete(self.articles[1])
        assert is_session_modified(self.session)

    def test_does_not_check_clean_objects(self, monkeypatch):
        checked = []

        def is_modified(obj):
            checked.append(obj)
            return False

        monkeypatch.setattr(utils, 'is_modified', is_modified)
        assert not is_session_modified(self.session)
        assert checked == []
