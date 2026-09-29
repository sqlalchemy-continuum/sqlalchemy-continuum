"""
Regression tests for issue #390: the per-transaction unit of work is stored on
``connection.info`` / ``session.info`` rather than in global dicts on the
``VersioningManager`` singleton, so versioning is thread-safe under connection
pools.

These tests are deterministic and run on every backend (including the default
in-memory SQLite), verifying the storage mechanism and its cleanup rather than
racing threads (see ``test_thread_safe_uow_multithreaded.py`` for the
concurrency stress test).
"""

import tempfile
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.pool import QueuePool

from sqlalchemy_continuum import UnitOfWork, versioning_manager
from sqlalchemy_continuum.manager import CONN_KEY, UOW_KEY
from tests import TestCase


class TestUnitOfWorkStorage(TestCase):
    plugins = []

    def test_manager_has_no_global_connection_state(self):
        # These global dicts were the source of the thread-safety races
        # (``dictionary changed size during iteration``); they must be gone.
        # This assertion fails on the pre-fix code.
        assert not hasattr(versioning_manager, 'units_of_work')
        assert not hasattr(versioning_manager, 'session_connection_map')

    def test_uow_lives_on_connection_info(self):
        article = self.Article(name='Some article')
        self.session.add(article)
        self.session.flush()

        connection = self.session.connection()
        uow = connection.info.get(UOW_KEY)
        assert isinstance(uow, UnitOfWork)
        # ``unit_of_work()`` resolves to the very same object.
        assert versioning_manager.unit_of_work(self.session) is uow
        # The session remembers its connection so it can be cleaned up at
        # commit time without calling ``session.connection()``.
        assert self.session.info.get(CONN_KEY) is connection

        self.session.commit()

    def test_state_cleared_after_commit(self):
        connection = self.session.connection()
        article = self.Article(name='Some article')
        self.session.add(article)
        self.session.commit()

        assert connection.info.get(UOW_KEY) is None
        assert self.session.info.get(CONN_KEY) is None

    def test_state_cleared_after_rollback(self):
        connection = self.session.connection()
        article = self.Article(name='Some article')
        self.session.add(article)
        self.session.flush()
        assert connection.info.get(UOW_KEY) is not None

        self.session.rollback()

        assert connection.info.get(UOW_KEY) is None
        assert self.session.info.get(CONN_KEY) is None


class TestPoolResetSafetyNet(TestCase):
    """
    The pool ``reset`` listener drops any lingering unit of work when a DBAPI
    connection is returned to the pool, so it can never leak into a later
    checkout of the same pooled connection (``connection.info`` persists across
    checkouts).
    """

    plugins = []

    def test_reset_clears_uow_before_next_checkout(self):
        # A real (non-singleton) pool is needed to exercise checkout/checkin,
        # so use a temporary file-based SQLite engine. ``make_versioned`` is
        # active for the duration of this TestCase, so its Engine-level
        # listeners apply to this engine too.
        with tempfile.TemporaryDirectory() as tmp:
            url = f'sqlite:///{Path(tmp) / "reset.db"}'
            engine = sa.create_engine(
                url, poolclass=QueuePool, pool_size=1, max_overflow=0
            )
            try:
                connection = engine.connect()
                uow = versioning_manager._uow_from_conn(connection)
                assert connection.info.get(UOW_KEY) is uow

                connection.close()  # return to pool -> reset listener fires

                reused = engine.connect()
                assert reused.info.get(UOW_KEY) is None
                reused.close()
            finally:
                engine.dispose()
