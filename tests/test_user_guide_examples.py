"""
Runtime verification of the code examples in the user guide (docs/).

Each test mirrors a documented example so that a change breaking the
documented API surfaces as a test failure, not as a stale docs page.
Comments reference the docs page the example comes from.
"""

from sqlalchemy_continuum import (
    Operation,
    changeset,
    count_versions,
    transaction_class,
    version_class,
)
from sqlalchemy_continuum.plugins import PropertyModTrackerPlugin
from tests import TestCase


class TestUserGuideQuickstart(TestCase):
    """README QuickStart and intro.md Basics."""

    def test_quickstart_flow(self):
        article = self.Article(name='Some article', content='Some content')
        self.session.add(article)
        self.session.commit()
        assert article.versions[0].name == 'Some article'

        article.name = 'Updated name'
        self.session.commit()
        assert article.versions[1].name == 'Updated name'

        article.versions[0].revert()
        assert article.name == 'Some article'

    def test_version_traversal(self):
        # version_objects.md: Version traversal
        article = self.Article(name='First')
        self.session.add(article)
        self.session.commit()
        article.name = 'Second'
        self.session.commit()

        first = article.versions[0]
        second = article.versions[1]
        assert first.index == 0
        assert first.next == second
        assert second.previous == first
        assert second.next is None

    def test_operation_types(self):
        # version_objects.md: Operation types
        article = self.Article(name='Some article')
        self.session.add(article)
        self.session.commit()
        assert article.versions[0].operation_type == Operation.INSERT
        article.name = 'Updated article'
        self.session.commit()
        assert article.versions[1].operation_type == Operation.UPDATE
        self.session.delete(article)
        self.session.commit()
        versions = (
            self.session.query(self.ArticleVersion)
            .order_by(getattr(self.ArticleVersion, self.transaction_column_name))
            .all()
        )
        assert versions[2].operation_type == Operation.DELETE


class TestUserGuideChangeset(TestCase):
    """version_objects.md: Changeset."""

    def test_version_changeset(self):
        article = self.Article(name='New article', content='Some content')
        self.session.add(article)
        self.session.commit()
        version = article.versions[0]
        assert version.changeset['name'] == [None, 'New article']

        article.name = 'Updated article'
        self.session.commit()
        assert article.versions[1].changeset['name'] == [
            'New article',
            'Updated article',
        ]

    def test_changeset_utility_and_count_versions(self):
        # utilities.md: changeset() and count_versions()
        article = self.Article(name='Some article')
        assert changeset(article) == {'name': ['Some article', None]}
        self.session.add(article)
        self.session.commit()
        assert count_versions(article) == 1


class TestUserGuideRevert(TestCase):
    """revert.md."""

    def test_revert_update(self):
        article = self.Article(name='New article', content='Some content')
        self.session.add(article)
        self.session.commit()
        article.name = 'Updated article'
        self.session.commit()

        article.versions[0].revert()
        self.session.commit()
        assert article.name == 'New article'

    def test_revert_delete(self):
        article = self.Article(name='New article', content='Some content')
        self.session.add(article)
        self.session.commit()
        old_id = article.id
        self.session.delete(article)
        self.session.commit()

        versions = (
            self.session.query(self.ArticleVersion).order_by(
                getattr(self.ArticleVersion, self.transaction_column_name)
            )
        ).all()
        resurrected = versions[0].revert()
        self.session.commit()
        assert resurrected.id == old_id
        assert self.session.query(self.Article).count() == 1

    def test_revert_relationships(self):
        article = self.Article(name='Some article')
        article.tags.append(self.Tag(name='Good'))
        article.tags.append(self.Tag(name='Interesting'))
        self.session.add(article)
        self.session.commit()

        tag = self.session.query(self.Tag).filter_by(name='Interesting').first()
        self.session.delete(tag)
        self.session.commit()
        assert len(article.tags) == 1

        article.versions[0].revert(relations=['tags'])
        self.session.commit()
        assert len(article.tags) == 2


class TestUserGuideQueries(TestCase):
    """queries.md (TransactionChangesPlugin is in the default plugin set)."""

    def _make_article_history(self):
        article = self.Article(name='some name')
        self.session.add(article)
        self.session.commit()
        article.name = 'other name'
        self.session.commit()
        return article

    def test_query_version_model(self):
        self._make_article_history()
        ArticleVersion = version_class(self.Article)
        results = self.session.query(ArticleVersion).filter_by(name='some name').all()
        assert len(results) == 1

    def test_transaction_count(self):
        self._make_article_history()
        Transaction = transaction_class(self.Article)
        assert self.session.query(Transaction).count() == 2

    def test_entities_at_a_given_revision(self):
        article = self._make_article_history()
        ArticleVersion = version_class(self.Article)
        tx_id = getattr(article.versions[0], self.transaction_column_name)
        results = (
            self.session.query(ArticleVersion)
            .filter_by(**{self.transaction_column_name: tx_id})
            .all()
        )
        assert results == [article.versions[0]]

    def test_transactions_that_changed_a_class(self):
        self._make_article_history()
        Transaction = transaction_class(self.Article)
        TransactionChanges = self.Article.__versioned__['transaction_changes']

        entries = (
            self.session.query(Transaction)
            .join(Transaction.changes)
            .filter(TransactionChanges.entity_name.in_(['Article']))
        )
        assert entries.count() == 2

    def test_version_at(self):
        article = self._make_article_history()
        ArticleVersion = version_class(self.Article)
        first_tx_id = getattr(article.versions[0], self.transaction_column_name)

        version = ArticleVersion.version_at(
            self.session, {'id': article.id}, transaction_id=first_tx_id
        )
        assert version is not None
        assert version.name == 'some name'

    def test_all_versions_with_linking(self):
        article = self._make_article_history()
        ArticleVersion = version_class(self.Article)

        versions = ArticleVersion.all_versions(
            self.session,
            {'id': article.id},
            desc=True,
            link=True,
        )
        assert len(versions) == 2
        # Newest first; linked caches make prev/next traversal query-free.
        assert versions[0].name == 'other name'
        assert versions[0].previous == versions[1]
        assert versions[1].next == versions[0]
        assert versions[1].previous is None


class TestUserGuidePropertyModTracker(TestCase):
    """queries.md: versions that modified a given property."""

    plugins = [PropertyModTrackerPlugin()]

    def test_query_by_property_mod_flag(self):
        article = self.Article(name='some name')
        self.session.add(article)
        self.session.commit()
        article.content = 'only content changed'
        self.session.commit()

        ArticleVersion = version_class(self.Article)
        results = (
            self.session.query(ArticleVersion).filter(ArticleVersion.name_mod).all()
        )
        assert len(results) == 1
        assert results[0].name == 'some name'
