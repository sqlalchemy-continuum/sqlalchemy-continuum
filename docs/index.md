# SQLAlchemy-Continuum

SQLAlchemy-Continuum is a versioning extension for SQLAlchemy.

## Features

- Creates versions for inserts, deletes and updates
- Does not store updates which don't change anything
- Supports alembic migrations
- Can revert objects data as well as all object relations at given transaction even if the object was deleted
- Transactions can be queried afterwards using SQLAlchemy query syntax
- Query for changed records at given transaction
- Temporal relationship reflection. Version object's relationship show the parent objects relationships as they where in that point in time.
- Supports native versioning for PostgreSQL database (trigger based versioning)

## Getting started

New to SQLAlchemy-Continuum? Start with the [Introduction](intro.md), which covers installation and basic usage.

## Documentation contents

- [Introduction](intro.md)
- [Version objects](version_objects.md)
- [Reverting changes](revert.md)
- [Queries](queries.md)
- [Transactions](transactions.md)
- [Native versioning](native_versioning.md)
- [Plugins](plugins.md)
- [Configuration](configuration.md)
- [Continuum schema](schema.md)
- [Alembic migrations](alembic.md)
- [Utilities](utilities.md)
- [API reference](api.md)
- [Changelog](changelog.md)
- [License](license.md)
