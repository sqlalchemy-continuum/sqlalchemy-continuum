import pytest
import sqlalchemy as sa
import sqlmodel

from sqlalchemy_continuum import Operation, versioning_manager
from tests import TestCase, create_test_cases

# SQLModel's Session deprecates query() and execute(), which the dynamic
# `versions` relationship and some version lookups still call.
pytestmark = pytest.mark.filterwarnings(
    r'ignore:\s*.*session\.exec\(\):DeprecationWarning'
)


class SQLModelTestCase(TestCase):
    @property
    def options(self):
        return {**super().options, 'base_classes': None}

    def setup_method(self, method):
        super().setup_method(method)
        self.session.close()
        self.session = sqlmodel.Session(self.connection, autoflush=False)


class SQLModelVersioningTestCase(SQLModelTestCase):
    user_cls = 'User'

    def create_models(self):
        # A registry per test, like the declarative_base() TestCase uses.
        class Model(sqlmodel.SQLModel, registry=sa.orm.registry()):
            pass

        class User(Model, table=True):
            id: int | None = sqlmodel.Field(default=None, primary_key=True)
            name: str

        class ArticleCategory(Model, table=True):
            article_id: int | None = sqlmodel.Field(
                default=None, foreign_key='article.id', primary_key=True
            )
            category_id: int | None = sqlmodel.Field(
                default=None, foreign_key='category.id', primary_key=True
            )

        class Article(Model, table=True):
            __versioned__ = {}

            id: int | None = sqlmodel.Field(default=None, primary_key=True)
            name: str
            tags: list['Tag'] = sqlmodel.Relationship(back_populates='article')
            categories: list['Category'] = sqlmodel.Relationship(
                back_populates='articles', link_model=ArticleCategory
            )

        class Tag(Model, table=True):
            __versioned__ = {}

            id: int | None = sqlmodel.Field(default=None, primary_key=True)
            name: str
            article_id: int | None = sqlmodel.Field(
                default=None, foreign_key='article.id'
            )
            article: Article | None = sqlmodel.Relationship(back_populates='tags')

        class Category(Model, table=True):
            __versioned__ = {}

            id: int | None = sqlmodel.Field(default=None, primary_key=True)
            name: str
            articles: list[Article] = sqlmodel.Relationship(
                back_populates='categories', link_model=ArticleCategory
            )

        self.Model = Model
        self.User = User
        self.Article = Article
        self.Tag = Tag
        self.Category = Category

    def test_builds_version_classes_on_the_model_registry(self):
        registry = sa.inspect(self.Article).registry
        Transaction = versioning_manager.transaction_cls
        assert sa.inspect(self.ArticleVersion).registry is registry
        assert sa.inspect(Transaction).registry is registry
        assert Transaction.user.property.mapper.class_ is self.User
        assert {
            'article_version',
            'tag_version',
            'category_version',
            'articlecategory_version',
            'transaction',
        } <= set(self.Model.metadata.tables)

    def test_delete(self):
        article = self.Article(name='Some article')
        self.session.add(article)
        self.session.commit()
        self.session.delete(article)
        self.session.commit()

        versions = self.session.exec(
            sqlmodel.select(self.ArticleVersion).order_by(
                self.ArticleVersion.transaction_id
            )
        ).all()
        assert [(v.name, v.operation_type) for v in versions] == [
            ('Some article', Operation.INSERT),
            ('Some article', Operation.DELETE),
        ]

    def test_one_to_many_relationship_versions(self):
        article = self.Article(name='Some article')
        article.tags.append(self.Tag(name='Some tag'))
        self.session.add(article)
        self.session.commit()

        article.name = 'Updated article'
        article.tags = []
        self.session.commit()
        assert [tag.name for tag in article.versions[0].tags] == ['Some tag']
        assert article.versions[1].tags == []

        article.versions[0].revert(relations=['tags'])
        self.session.commit()
        assert [tag.name for tag in article.tags] == ['Some tag']

    def test_many_to_many_relationship_versions(self):
        article = self.Article(name='Some article')
        article.categories.append(self.Category(name='Some category'))
        self.session.add(article)
        self.session.commit()

        article.name = 'Updated article'
        article.categories = []
        self.session.commit()
        assert [c.name for c in article.versions[0].categories] == ['Some category']
        assert article.versions[1].categories == []


create_test_cases(
    SQLModelVersioningTestCase, {'versioning_strategy': ['subquery', 'validity']}
)


# Mirrors the example in docs/sqlmodel.md, which uses SQLModel's default
# registry rather than one per test.
class TestSQLModelUserGuide(SQLModelTestCase):
    def create_models(self):
        class Article(sqlmodel.SQLModel, table=True):
            __versioned__ = {}

            id: int | None = sqlmodel.Field(default=None, primary_key=True)
            name: str

        self.Model = sqlmodel.SQLModel
        self.Article = Article

    def teardown_method(self, method):
        super().teardown_method(method)
        # The default registry is process-wide; drop this test's classes and
        # tables so later declarations of the same names don't collide.
        self.Model.metadata.clear()
        sa.inspect(self.Article).registry.dispose()

    def test_versions_and_revert(self):
        assert {'article_version', 'transaction'} <= set(self.Model.metadata.tables)

        article = self.Article(name='Some article')
        self.session.add(article)
        self.session.commit()

        article.name = 'Updated article'
        self.session.commit()
        assert [version.name for version in article.versions] == [
            'Some article',
            'Updated article',
        ]

        article.versions[0].revert()
        self.session.commit()
        assert article.name == 'Some article'
