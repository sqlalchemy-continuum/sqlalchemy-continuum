"""Tests for efficient version query features."""

from tests import TestCase, create_test_cases, setting_variants


class EfficientQueriesTestCase(TestCase):
    """Test efficient version query methods."""

    def _create_article_with_versions(self, num_versions=4):
        """Helper to create an article with multiple versions."""
        names = [f'Version {i}' for i in range(num_versions)]

        article = self.Article(name=names[0])
        self.session.add(article)
        self.session.commit()

        for name in names[1:]:
            article.name = name
            self.session.commit()

        return article, names

    def _get_tx_id(self, version_obj):
        """Get the transaction ID from a version object, handling custom column names."""
        return getattr(version_obj, self.transaction_column_name)

    def test_version_at_returns_correct_version(self):
        """Test that version_at returns the version active at a given transaction."""
        article, names = self._create_article_with_versions(4)

        # Get all versions to find their transaction IDs
        versions = list(article.versions)

        # Query for version at the second transaction
        target_tx = self._get_tx_id(versions[1])
        result = self.ArticleVersion.version_at(
            self.session, {'id': article.id}, transaction_id=target_tx
        )

        assert result is not None
        assert result.name == names[1]
        assert self._get_tx_id(result) == target_tx

    def test_version_at_returns_none_for_nonexistent(self):
        """Test that version_at returns None when no version exists."""
        article, _ = self._create_article_with_versions(2)

        # Query for a transaction ID that doesn't exist (before first version)
        result = self.ArticleVersion.version_at(
            self.session, {'id': article.id}, transaction_id=0
        )

        assert result is None

    def test_version_at_with_wrong_primary_key(self):
        """Test that version_at returns None for non-existent entity."""
        article, _ = self._create_article_with_versions(2)

        versions = list(article.versions)
        target_tx = self._get_tx_id(versions[0])

        result = self.ArticleVersion.version_at(
            self.session,
            {'id': 99999},  # Non-existent ID
            transaction_id=target_tx,
        )

        assert result is None

    def test_all_versions_returns_all(self):
        """Test that all_versions returns all versions of an entity."""
        article, names = self._create_article_with_versions(4)

        versions = self.ArticleVersion.all_versions(self.session, {'id': article.id})

        assert len(versions) == 4
        # Default is desc=True, so newest first
        assert versions[0].name == names[3]
        assert versions[3].name == names[0]

    def test_all_versions_with_limit(self):
        """Test that all_versions respects limit parameter."""
        article, names = self._create_article_with_versions(4)

        versions = self.ArticleVersion.all_versions(
            self.session, {'id': article.id}, limit=2
        )

        assert len(versions) == 2
        # Should get the 2 most recent (desc=True by default)
        assert versions[0].name == names[3]
        assert versions[1].name == names[2]

    def test_all_versions_with_offset(self):
        """Test that all_versions respects offset parameter."""
        article, names = self._create_article_with_versions(4)

        versions = self.ArticleVersion.all_versions(
            self.session, {'id': article.id}, offset=1, limit=2
        )

        assert len(versions) == 2
        # Skip first (newest), get next 2
        assert versions[0].name == names[2]
        assert versions[1].name == names[1]

    def test_all_versions_ascending_order(self):
        """Test that all_versions can return in ascending order."""
        article, names = self._create_article_with_versions(4)

        versions = self.ArticleVersion.all_versions(
            self.session, {'id': article.id}, desc=False
        )

        assert len(versions) == 4
        # Oldest first
        assert versions[0].name == names[0]
        assert versions[3].name == names[3]

    def test_all_versions_links_previous_next(self):
        """Test that all_versions with link=True pre-populates caches."""
        article, names = self._create_article_with_versions(4)

        versions = self.ArticleVersion.all_versions(
            self.session,
            {'id': article.id},
            link=True,  # Default
        )

        # Check that caches are populated
        assert versions[0]._cache_populated is True
        assert versions[0].next is None  # Newest has no next
        assert versions[0].previous == versions[1]

        assert versions[1].next == versions[0]
        assert versions[1].previous == versions[2]

        assert versions[3].previous is None  # Oldest has no previous
        assert versions[3].next == versions[2]

    def test_all_versions_no_link(self):
        """Test that all_versions with link=False doesn't populate caches."""
        article, _ = self._create_article_with_versions(4)

        versions = self.ArticleVersion.all_versions(
            self.session, {'id': article.id}, link=False
        )

        # Caches should not be populated
        assert (
            not hasattr(versions[0], '_cache_populated')
            or not versions[0]._cache_populated
        )

    def test_all_versions_ascending_links_correctly(self):
        """Test that link_versions works correctly with ascending order."""
        article, names = self._create_article_with_versions(4)

        versions = self.ArticleVersion.all_versions(
            self.session,
            {'id': article.id},
            desc=False,  # Ascending - oldest first
            link=True,
        )

        # In ascending order: versions[0] is oldest, versions[-1] is newest
        assert versions[0].previous is None  # Oldest has no previous
        assert versions[0].next == versions[1]

        assert versions[3].next is None  # Newest has no next
        assert versions[3].previous == versions[2]


class CompositeIndexTestCase(TestCase):
    """Test that composite indexes are created correctly."""

    def test_composite_index_exists_by_default(self):
        """Test that composite index is created by default."""
        # Get the version table
        version_table = self.ArticleVersion.__table__

        # Check for index with pattern ix_<table>_pk_transaction_id
        index_names = [idx.name for idx in version_table.indexes]

        expected_index = f'ix_{version_table.name}_pk_transaction_id'
        assert expected_index in index_names, (
            f'Expected index {expected_index} not found in {index_names}'
        )

    def test_validity_strategy_creates_validity_index(self):
        """Test that validity strategy creates additional validity index."""
        if self.versioning_strategy != 'validity':
            return  # Skip for subquery strategy

        version_table = self.ArticleVersion.__table__

        index_names = [idx.name for idx in version_table.indexes]

        expected_index = f'ix_{version_table.name}_pk_validity'
        assert expected_index in index_names, (
            f'Expected index {expected_index} not found in {index_names}'
        )


# Create test cases for all strategy variants
create_test_cases(EfficientQueriesTestCase, setting_variants)
create_test_cases(CompositeIndexTestCase, setting_variants)
