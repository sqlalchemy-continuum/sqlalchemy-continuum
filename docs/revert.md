# Reverting changes

One of the major benefits of SQLAlchemy-Continuum is its ability to revert changes.

## Revert update

```python
article = Article(name='New article', content='Some content')
session.add(article)
session.commit()

version = article.versions[0]
article.name = 'Updated article'
session.commit()

version.revert()
session.commit()

article.name
# 'New article'
```

## Revert delete

```python
article = Article(name='New article', content='Some content')
session.add(article)
session.commit()

version = article.versions[0]
session.delete(article)
session.commit()

version.revert()
session.commit()

# article lives again!
session.query(Article).first()
```

## Revert relationships

Sometimes you may have cases where you want to revert an object as well as some of its relation to certain state. Consider the following model definition:

```python
class Article(Base):
    __tablename__ = 'article'
    __versioned__ = {}

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)
    name = sa.Column(sa.Unicode(255))


class Tag(Base):
    __tablename__ = 'tag'
    __versioned__ = {}

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)
    name = sa.Column(sa.Unicode(255))
    article_id = sa.Column(sa.Integer, sa.ForeignKey(Article.id))
    article = sa.orm.relationship(Article, backref='tags')
```

Now lets say some user first adds an article with couple of tags:

```python
article = Article(
    name='Some article',
    tags=[Tag(name='Good'), Tag(name='Interesting')]
)

session.add(article)
session.commit()
```

Then lets say another user deletes one of the tags:

```python
tag = session.query(Tag).filter_by(name='Interesting').first()

session.delete(tag)
session.commit()
```

Now the first user wants to set the article back to its original state. It can be achieved as follows (notice how we use the relations parameter):

```python
article = session.get(Article, 1)
article.versions[0].revert(relations=['tags'])
session.commit()
```
