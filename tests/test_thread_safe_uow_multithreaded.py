"""
Concurrency stress test for issue #390.

Many threads share a single ``Engine`` (and therefore its connection pool) and
each drives its own session through insert + update + commit cycles. On the
pre-fix code the global ``VersioningManager`` dicts are mutated and iterated
from several threads at once, which raised ``RuntimeError: dictionary changed
size during iteration`` / ``KeyError``. With per-connection ``.info`` storage
each thread works on its own connection, so no shared mutable state is touched.

Skipped on SQLite: the in-memory database serves every connection from a single
shared DBAPI connection, so it cannot exercise real multi-connection
concurrency (the concurrency matrix runs this on postgres/mysql in CI).
"""

import os
from threading import Thread, current_thread

import pytest
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from tests import TestCase

NUM_ROWS = 50
NUM_THREADS = 8


class RaisingThread(Thread):
    """``threading.Thread`` that re-raises any worker exception on ``join``."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exc = None

    def run(self):
        try:
            super().run()
        except BaseException as e:  # noqa: BLE001 - re-raised in join()
            self.exc = e

    def join(self, timeout=None):
        super().join(timeout)
        if self.exc:
            raise self.exc


class TestConcurrentVersioning(TestCase):
    plugins = []

    @pytest.mark.skipif("os.environ.get('DB', 'sqlite') == 'sqlite'")
    def test_concurrent_sessions_on_shared_engine_pool(self):
        threads = [RaisingThread(target=self._worker) for _ in range(NUM_THREADS)]

        for thread in threads:
            thread.start()

        # A race in any worker is re-raised here and fails the test.
        for thread in threads:
            thread.join()

    def _worker(self):
        Session = sessionmaker(bind=self.engine)
        session = Session(autoflush=False)
        name = current_thread().name
        try:
            for i in range(NUM_ROWS):
                article = self.Article(name=f'{name}-{i:04}')
                session.add(article)
                session.commit()  # -> insert version row
                article.name += '-v2'
                session.commit()  # -> update version row

            # Every parent row exists...
            assert (
                session.query(func.count(self.Article.id))
                .where(self.Article.name.like(f'{name}-%'))
                .scalar()
                == NUM_ROWS
            )
            # ...and both the insert and the update were versioned (2 each).
            assert (
                session.query(func.count())
                .select_from(self.ArticleVersion)
                .where(self.ArticleVersion.name.like(f'{name}-%'))
                .scalar()
                == NUM_ROWS * 2
            )
        finally:
            session.close()
