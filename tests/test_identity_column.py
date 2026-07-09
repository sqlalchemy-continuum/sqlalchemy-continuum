"""
Tests for SQLAlchemy Identity object support in version tables.

This addresses issue #359: Support for SQLAlchemy Identity object
https://github.com/sqlalchemy-continuum/sqlalchemy-continuum/issues/359
"""
from copy import copy

import pytest
import sqlalchemy as sa
from sqlalchemy.schema import Identity

from sqlalchemy_continuum import version_class
from tests import TestCase


class TestIdentityColumnWithAlwaysTrue(TestCase):
    """Test Identity columns with always=True parameter."""

    def create_models(self):
        class Article(self.Model):
            __tablename__ = 'article'
            __versioned__ = copy(self.options)

            id: sa.Mapped[int] = sa.Column(
                sa.Integer,
                server_default=Identity(start=1, increment=1, always=True),
                primary_key=True,
                autoincrement=True,
            )
            name = sa.Column(sa.Unicode(255), nullable=False)
            content = sa.Column(sa.UnicodeText)

        self.Article = Article

    def test_version_table_created_without_identity(self):
        """Version table should not have Identity constraint."""
        table = version_class(self.Article).__table__
        
        # Version table should exist
        assert 'id' in table.c
        
        # The id column should NOT have an Identity server_default
        # (it should be None or not an Identity object)
        id_column = table.c.id
        assert not isinstance(id_column.server_default, Identity), \
            "Version table should not have Identity constraint on id column"

    def test_version_table_has_autoincrement_false(self):
        """Version table id column should have autoincrement=False."""
        table = version_class(self.Article).__table__
        assert table.c.id.autoincrement is False

    def test_insert_record_creates_version(self):
        """Test that inserting a record creates a version entry."""
        article = self.Article()
        article.name = 'Test Article'
        article.content = 'Test Content'
        self.session.add(article)
        self.session.commit()

        # Should create a version
        versions = list(article.versions)
        assert len(versions) == 1
        assert versions[0].name == 'Test Article'
        assert versions[0].content == 'Test Content'

    def test_update_record_creates_version(self):
        """Test that updating a record creates a new version entry."""
        article = self.Article()
        article.name = 'Original Name'
        article.content = 'Original Content'
        self.session.add(article)
        self.session.commit()

        # Update the article
        article.name = 'Updated Name'
        self.session.commit()

        # Should have two versions
        versions = list(article.versions)
        assert len(versions) == 2
        assert versions[0].name == 'Original Name'
        assert versions[1].name == 'Updated Name'


class TestIdentityColumnWithAlwaysFalse(TestCase):
    """Test Identity columns with always=False parameter."""

    def create_models(self):
        class Article(self.Model):
            __tablename__ = 'article'
            __versioned__ = copy(self.options)

            id: sa.Mapped[int] = sa.Column(
                sa.Integer,
                server_default=Identity(start=1, increment=1, always=False),
                primary_key=True,
                autoincrement=True,
            )
            name = sa.Column(sa.Unicode(255), nullable=False)

        self.Article = Article

    def test_version_table_created_without_identity(self):
        """Version table should not have Identity constraint even with always=False."""
        table = version_class(self.Article).__table__
        
        id_column = table.c.id
        assert not isinstance(id_column.server_default, Identity), \
            "Version table should not have Identity constraint on id column"

    def test_insert_and_version_creation(self):
        """Test basic insert and version creation with always=False."""
        article = self.Article()
        article.name = 'Test Article'
        self.session.add(article)
        self.session.commit()

        versions = list(article.versions)
        assert len(versions) == 1
        assert versions[0].name == 'Test Article'


class TestIdentityOnNonPrimaryKeyColumn(TestCase):
    """Test Identity on non-primary key columns."""

    def create_models(self):
        class Article(self.Model):
            __tablename__ = 'article'
            __versioned__ = copy(self.options)

            id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
            sequence_num = sa.Column(
                sa.Integer,
                server_default=Identity(start=1, increment=1, always=True),
            )
            name = sa.Column(sa.Unicode(255))

        self.Article = Article

    def test_version_table_non_pk_identity_removed(self):
        """Version table should not have Identity on non-PK columns either."""
        table = version_class(self.Article).__table__
        
        # Check that sequence_num column exists but has no Identity
        assert 'sequence_num' in table.c
        seq_column = table.c.sequence_num
        assert not isinstance(seq_column.server_default, Identity), \
            "Version table should not have Identity constraint on non-PK columns"

