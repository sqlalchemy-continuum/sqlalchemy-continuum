# SQLModel

SQLAlchemy-Continuum versions [SQLModel](https://sqlmodel.tiangolo.com) table models the same way as plain SQLAlchemy models. Call `make_versioned()` before your models are defined, add `__versioned__` to the models you want to version and call `configure_mappers()` once all of them are defined. SQLModel requires SQLAlchemy 2.0 or newer.

```python
import sqlalchemy as sa
from sqlmodel import Field, Session, SQLModel, create_engine

from sqlalchemy_continuum import make_versioned


make_versioned(user_cls=None)


class Article(SQLModel, table=True):
    __versioned__ = {}

    id: int | None = Field(default=None, primary_key=True)
    name: str


# after you have defined all your models, call configure_mappers:
sa.orm.configure_mappers()

engine = create_engine('sqlite://')
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    article = Article(name='Some article')
    session.add(article)
    session.commit()

    article.name = 'Updated article'
    session.commit()

    article.versions[0].name  # 'Some article'

    article.versions[0].revert()
    session.commit()
    article.name  # 'Some article'
```

The version tables and the `transaction` table are added to the metadata of your models (`SQLModel.metadata` by default), so `create_all()` and [Alembic](alembic.md) autogenerate pick them up.

The generated version classes are plain SQLAlchemy declarative classes on the registry of your models, not SQLModel classes. If you set the `base_classes` [option](configuration.md), list declarative classes there; SQLModel classes can't be used as version class bases.

SQLModel's `Session` deprecates `query()` and `execute()`, which the `versions` relationship and some version lookups still call, so your test runs may show SQLModel's `DeprecationWarning`. It doesn't affect versioning.
