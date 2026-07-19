import sqlalchemy as sa
from pytest import raises
from sqlmodel import Field, Relationship

from sqlalchemy_continuum.reverter import Reverter, ReverterException
from tests.sqlmodel import SQLModelTestCase


class TestReverter(SQLModelTestCase):
    def test_raises_exception_for_unknown_relations(self):
        article = self.Article()
        article = self.Article(name='Some article', content='Some content')
        self.session.add(article)

        self.session.commit()
        version = article.versions[0]

        with raises(ReverterException):
            Reverter(version, relations=['unknown_relation'])


class RevertTestCase(SQLModelTestCase):
    def add_article(self):
        article = self.Article(name='Some article', content='Some content')
        self.session.add(article)
        self.session.commit()
        return article

    def test_simple_revert(self):
        article = self.add_article()
        article.name = 'Updated name'
        article.content = 'Updated content'
        self.session.commit()
        self.session.refresh(article)
        article.versions[0].revert()
        assert article.name == 'Some article'
        assert article.content == 'Some content'

    def test_revert_deleted_model(self):
        article = self.add_article()
        old_article_id = article.id
        version = article.versions[0]
        self.session.delete(article)
        self.session.commit()
        version.revert()
        assert article.id == old_article_id
        assert article.name == 'Some article'
        assert article.content == 'Some content'

    def test_revert_deletion(self):
        article = self.add_article()
        old_article_id = article.id
        version = article.versions[0]
        self.session.delete(article)
        self.session.commit()
        version.revert()
        self.session.commit()
        assert (
            self.session.scalar(sa.select(sa.func.count()).select_from(self.Article))
            == 1
        )

        article = self.session.get(self.Article, old_article_id)

        assert version.next.next

        version.next.revert()
        self.session.commit()
        assert not self.session.get(self.Article, old_article_id)

    def test_revert_version_with_one_to_many_relation(self):
        article = self.Article(name='Some article', content='Some content')
        article.tags.append(self.Tag(name='some tag'))
        self.session.add(article)
        self.session.commit()
        article.name = 'Updated name'
        article.content = 'Updated content'
        article.tags = []
        self.session.commit()
        self.session.refresh(article)
        assert article.tags == []
        assert len(article.versions[0].tags) == 1
        assert article.versions[0].tags[0].article
        article.versions[0].revert(relations=['tags'])
        self.session.commit()

        assert article.name == 'Some article'
        assert article.content == 'Some content'
        assert len(article.tags) == 1
        assert article.tags[0].name == 'some tag'

    def test_with_one_to_many_relation_delete_newly_added(self):
        article = self.Article(name='Some article', content='Some content')
        article.tags.append(self.Tag(name='some tag'))
        self.session.add(article)
        self.session.commit()
        article.name = 'Updated name'
        article.content = 'Updated content'
        article.tags.append(self.Tag(name='some other tag'))
        self.session.add(article)
        self.session.commit()
        self.session.refresh(article)
        assert len(article.tags) == 2
        assert len(article.versions[0].tags) == 1
        assert article.versions[0].tags[0].article
        article.versions[0].revert(relations=['tags'])
        self.session.commit()

        assert article.name == 'Some article'
        assert article.content == 'Some content'
        assert len(article.tags) == 1
        assert article.tags[0].name == 'some tag'

    def test_with_one_to_many_relation_resurrect_deleted(self):
        article = self.Article(name='Some article', content='Some content')
        tag = self.Tag(name='some other tag')
        article.tags.append(self.Tag(name='some tag'))
        article.tags.append(tag)
        self.session.add(article)
        self.session.commit()
        article.name = 'Updated name'
        article.tags.remove(tag)
        self.session.add(article)
        self.session.commit()
        self.session.refresh(article)
        assert len(article.tags) == 1
        assert len(article.versions[0].tags) == 2
        article.versions[0].revert(relations=['tags'])
        self.session.commit()
        assert len(article.tags) == 2
        assert article.tags[0].name == 'some tag'


class TestRevertWithDefaultVersioningStrategy(RevertTestCase):
    pass


class TestRevertWithValidityVersioningStrategy(RevertTestCase):
    versioning_strategy = 'validity'


class TestRevertWithCustomTransactionColumn(RevertTestCase):
    transaction_column_name = 'tx_id'


class TestRevertWithColumnExclusion(RevertTestCase):
    def create_models(self):
        class Article(self.Model, table=True):
            __tablename__ = 'article'
            __versioned__ = {'exclude': ['description']}

            id: int = Field(sa_type=sa.Integer, primary_key=True)
            name: str = Field(sa_type=sa.Unicode(255), nullable=False)
            content: str = Field(sa_type=sa.UnicodeText)
            description: str = Field(
                sa_type=sa.UnicodeText, default=None, nullable=True
            )
            tags: list['Tag'] = Relationship(back_populates='article')

        class Tag(self.Model, table=True):
            __tablename__ = 'tag'
            __versioned__ = {}

            id: int = Field(sa_type=sa.Integer, primary_key=True)
            name: str = Field(sa_type=sa.Unicode(255))
            article_id: int | None = Field(default=None, foreign_key='article.id')
            article: Article = Relationship(back_populates='tags')

        self.Article = Article
        self.Tag = Tag
