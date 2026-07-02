# Queries

You can query history models just like any other sqlalchemy declarative model.

```python
from sqlalchemy_continuum import version_class


ArticleVersion = version_class(Article)

session.query(ArticleVersion).filter_by(name='some name').all()
```

## How many transactions have been executed?

```python
from sqlalchemy_continuum import transaction_class


Transaction = transaction_class(Article)


session.query(Transaction).count()
```

## Querying for entities of a class at a given revision

In the following example we find all articles which were affected by transaction 33.

```python
session.query(ArticleVersion).filter_by(transaction_id=33)
```

## Querying for transactions, at which entities of a given class changed

In this example we find all transactions which affected any instance of 'Article' model. This query needs the TransactionChangesPlugin.

```python
Transaction = transaction_class(Article)

TransactionChanges = Article.__versioned__['transaction_changes']


entries = (
    session.query(Transaction)
    .join(Transaction.changes)
    .filter(
        TransactionChanges.entity_name.in_(['Article'])
    )
)
```

## Querying for versions of entity that modified given property

In the following example we want to find all versions of Article class which changed the attribute 'name'. This example assumes you are using
PropertyModTrackerPlugin.

```python
ArticleVersion = version_class(Article)

session.query(ArticleVersion).filter(ArticleVersion.name_mod).all()
```

## Efficient version queries

SQLAlchemy-Continuum provides several methods for efficiently querying version history
without incurring N+1 query problems.

### Querying version at a specific transaction

The `version_at` class method efficiently retrieves the version that was active
at a specific transaction. This is much faster than iterating through versions manually.

```python
ArticleVersion = version_class(Article)

# Get the version of Article #5 that was active at transaction #100
version = ArticleVersion.version_at(
    session,
    {'id': 5},
    transaction_id=100
)
```

For the validity strategy (default), this uses an efficient range query:

```sql
WHERE transaction_id <= 100
  AND (end_transaction_id > 100 OR end_transaction_id IS NULL)
```

For the subquery strategy, it finds the version with the highest transaction_id <= target.

### Batch fetching all versions

When you need to iterate through version history, avoid the N+1 query problem by
using `all_versions` instead of repeatedly accessing `.previous` or `.next`:

```python
ArticleVersion = version_class(Article)

# Fetch all versions for Article #5 in a single query
versions = ArticleVersion.all_versions(
    session,
    {'id': 5},
    limit=10,      # Optional: limit to 10 most recent
    desc=True,     # Newest first (default)
    link=True      # Pre-populate previous/next caches (default)
)

# Now iteration doesn't trigger additional queries
for version in versions:
    print(version.changeset)
    print(version.previous)  # Uses cached value, no additional query!
```

When `link=True` (the default), the returned versions will have their `.previous`
and `.next` properties pre-populated from the fetched results. This means accessing
these properties won't trigger additional database queries.

**Anti-pattern to avoid:**

```python
# BAD: This triggers N queries for N versions!
version = article.versions[-1]
while version:
    process(version)
    version = version.previous  # Each call is a separate query
```

**Recommended pattern:**

```python
# GOOD: Single query, then iterate in memory
versions = ArticleVersion.all_versions(
    session,
    {'id': article.id}
)
for version in versions:
    process(version)
```

## Index recommendations

SQLAlchemy-Continuum automatically creates several indexes on version tables.
Understanding these indexes helps you write efficient queries.

### Automatic Indexes

The following indexes are created automatically:

* `transaction_id` - Primary key index (always present)
* `end_transaction_id` - For validity strategy (enables efficient range queries)
* `operation_type` - For filtering INSERT/UPDATE/DELETE operations

Starting with version 1.6.0, composite indexes are also created by default:

* `(primary_keys, transaction_id DESC)` - For efficient entity version lookups
* `(primary_keys, transaction_id, end_transaction_id)` - For validity strategy temporal queries

These composite indexes dramatically speed up the most common query patterns.

### Disabling Composite Indexes

If you need to disable automatic composite index creation (e.g., for migration compatibility),
you can set the `create_composite_index` option to `False`:

```python
make_versioned(options={'create_composite_index': False})
```

Or per-model:

```python
class Article(Base):
    __versioned__ = {
        'create_composite_index': False
    }
```

### Recommended Additional Indexes

Depending on your query patterns, you may want to add these additional indexes:

**For queries filtering by operation type and entity:**

```python
from sqlalchemy import Index

Index(
    'ix_article_version_id_operation',
    ArticleVersion.id,
    ArticleVersion.operation_type,
    ArticleVersion.transaction_id
)
```

**For queries joining with Transaction table on issued_at:**

If you frequently query versions by timestamp (e.g., "give me the version as of 2023-01-01"),
ensure you have an index on `Transaction.issued_at`:

```python
Index('ix_transaction_issued_at', Transaction.issued_at.desc())
```

**For PropertyModTrackerPlugin queries:**

If you use PropertyModTrackerPlugin and frequently query for versions where specific
fields changed, consider partial indexes:

```python
# PostgreSQL partial index example
Index(
    'ix_article_version_name_mod',
    ArticleVersion.id,
    postgresql_where=ArticleVersion.name_mod.is_(True)
)
```

### Query Performance Tips

1. **Use the validity strategy** (default) for read-heavy workloads. It enables
   O(log N) version lookups via direct equality conditions instead of correlated subqueries.

2. **Batch fetch versions** using `all_versions()` instead of iterating with `.previous`/`.next`.

3. **Add composite indexes** on `(entity_pk, transaction_id)` for your most-queried version tables.

4. **Use LIMIT** when you only need recent versions:

    ```python
    ArticleVersion.all_versions(session, {'id': 5}, limit=10)
    ```

5. **Avoid relationship traversal** on version objects when possible. Relationship queries
   on versions generate complex subqueries. If you need related data, fetch from the
   parent object first or use explicit joins.
