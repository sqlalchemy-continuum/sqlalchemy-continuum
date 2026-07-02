# Plugins

## Using plugins

```python
from sqlalchemy_continuum import versioning_manager
from sqlalchemy_continuum.plugins import PropertyModTrackerPlugin


versioning_manager.plugins.append(PropertyModTrackerPlugin())


versioning_manager.plugins  # <PluginCollection [...]>

# You can also remove plugin

del versioning_manager.plugins[0]
```

## Activity

The ActivityPlugin is the most powerful plugin for tracking changes of
individual entities. If you use ActivityPlugin you probably don't need to use
TransactionChanges nor TransactionMeta plugins.

You can initalize the ActivityPlugin by adding it to versioning manager.

```python
activity_plugin = ActivityPlugin()

make_versioned(plugins=[activity_plugin])
```

ActivityPlugin uses single database table for tracking activities. This table
follows the data structure in [activity stream specification](http://www.activitystrea.ms), but it comes
with a nice twist:

| Column         | Type       | Description |
|----------------|------------|-------------|
| id             | BigInteger | The primary key of the activity |
| verb           | Unicode    | Verb defines the action of the activity |
| data           | JSON       | Additional data for the activity in JSON format |
| transaction_id | BigInteger | The transaction this activity was associated with |
| object_id      | BigInteger | The primary key of the object. Object can be any entity which has an integer as primary key. |
| object_type    | Unicode    | The type of the object (class name as string) |
| object_tx_id   | BigInteger | The last transaction_id associated with the object. This is used for efficiently fetching the object version associated with this activity. |
| target_id      | BigInteger | The primary key of the target. Target can be any entity which has an integer as primary key. |
| target_type    | Unicode    | The of the target (class name as string) |
| target_tx_id   | BigInteger | The last transaction_id associated with the target. |

Each Activity has relationships to actor, object and target but it also holds
information about the associated transaction and about the last associated
transactions with the target and object. This allows each activity to also have
object_version and target_version relationships for introspecting what those
objects and targets were in given point in time. All these relationship
properties use [generic relationships](https://sqlalchemy-utils.readthedocs.io/en/latest/generic_relationship.html) of the SQLAlchemy-Utils package.

### Limitations

Currently all changes to parent models must be flushed or committed before
creating activities. This is due to a fact that there is still no dependency
processors for generic relationships. So when you create activities and assign
objects / targets for those please remember to flush the session before
creating an activity:

```python
article = Article(name=u'Some article')
session.add(article)
session.flush()  # <- IMPORTANT!
first_activity = Activity(verb=u'create', object=article)
session.add(first_activity)
session.commit()
```

Targets and objects of given activity must have an integer primary key
column id.

### Create activities

Once your models have been configured you can get the Activity model from the
ActivityPlugin class with activity_cls property:

```python
Activity = activity_plugin.activity_cls
```

Now let's say we have model called Article and Category. Each Article has one
Category. Activities should be created along with the changes you make on
these models.

```python
article = Article(name=u'Some article')
session.add(article)
session.flush()
first_activity = Activity(verb=u'create', object=article)
session.add(first_activity)
session.commit()
```

Current transaction gets automatically assigned to activity object:

```python
first_activity.transaction  # Transaction object
```

### Update activities

The object property of the Activity object holds the current object and the
object_version holds the object version at the time when the activity was
created.

```python
article.name = u'Some article updated!'
session.flush()
second_activity = Activity(verb=u'update', object=article)
session.add(second_activity)
session.commit()

second_activity.object.name  # u'Some article updated!'
first_activity.object.name  # u'Some article updated!'

first_activity.object_version.name  # u'Some article'
```

### Delete activities

The version properties are especially useful for delete activities. Once the
activity is fetched from the database the object is no longer available (
since its deleted), hence the only way we could show some information about the
object the user deleted is by accessing the object_version property.

```python
session.delete(article)
session.flush()
third_activity = Activity(verb=u'delete', object=article)
session.add(third_activity)
session.commit()

third_activity.object_version.name  # u'Some article updated!'
```

### Local version histories using targets

The target property of the Activity model offers a way of tracking changes of
given related object. In the example below we create a new activity when adding
a category for article and then mark the article as the target of this
activity.

```python
session.add(Category(name=u'Fist category', article=article))
session.flush()
activity = Activity(
    verb=u'create',
    object=category,
    target=article
)
session.add(activity)
session.commit()
```

Now if we wanted to find all the changes that affected given article we could
do so by searching through all the activities where either the object or
target is the given article.

```python
import sqlalchemy as sa


activities = session.query(Activity).filter(
    sa.or_(
        Activity.object == article,
        Activity.target == article
    )
)
```

## Flask

FlaskPlugin offers way of integrating Flask framework with
SQLAlchemy-Continuum. Flask-Plugin adds two columns for Transaction model,
namely `user_id` and `remote_addr`.

These columns are automatically populated when transaction object is created.
The `remote_addr` column is populated with the value of the remote address that
made current request. The `user_id` column is populated with the id of the
current_user object.

```python
from sqlalchemy_continuum.plugins import FlaskPlugin
from sqlalchemy_continuum import make_versioned


make_versioned(plugins=[FlaskPlugin()])
```

## PropertyModTracker

The PropertyModTrackerPlugin offers a way of efficiently tracking individual
property modifications. With PropertyModTrackerPlugin you can make efficient
queries such as:

Find all versions of model X where user updated the property A or property B.

Find all versions of model X where user didn't update property A.

PropertyModTrackerPlugin adds separate modified tracking column for each
versioned column. So for example if you have versioned model called Article
with columns `name` and `content`, this plugin would add two additional boolean
columns `name_mod` and `content_mod` for the version model. When user commits
transactions the plugin automatically updates these boolean columns.

## TransactionChanges

TransactionChanges provides way of keeping track efficiently which declarative
models were changed in given transaction. This can be useful when transactions
need to be queried afterwards for problems such as:

1. Find all transactions which affected `User` model.

2. Find all transactions which didn't affect models `Entity` and `Event`.

The plugin works in two ways. On class instrumentation phase this plugin
creates a special transaction model called `TransactionChanges`. This model is
associated with table called `transaction_changes`, which has only only two
fields: transaction_id and entity_name. If for example transaction consisted
of saving 5 new User entities and 1 Article entity, two new rows would be
inserted into transaction_changes table.

| transaction_id | entity_name |
|----------------|-------------|
| 233678         | User        |
| 233678         | Article     |

## TransactionMeta

TransactionMetaPlugin offers a way of saving key-value data for transations.
You can use the plugin in same way as other plugins:

```python
meta_plugin = TransactionMetaPlugin()

versioning_manager.plugins.append(meta_plugin)
```

TransactionMetaPlugin creates a simple model called TransactionMeta. This class
has three columns: transaction_id, key and value. TransactionMeta plugin also
creates an association proxy between TransactionMeta and Transaction classes
for easy dictionary based access of key-value pairs.

You can easily 'tag' transactions with certain key value pairs by giving these
keys and values to the meta property of Transaction class.

```python
from sqlalchemy_continuum import versioning_manager


article = Article()
session.add(article)

uow = versioning_manager.unit_of_work(session)
tx = uow.create_transaction(session)
tx.meta = {u'some_key': u'some value'}
session.commit()

TransactionMeta = meta_plugin.model_class
Transaction = versioning_manager.transaction_cls

# find all transactions with 'article' tags
query = (
    session.query(Transaction)
    .join(Transaction.meta_relation)
    .filter(
        db.and_(
            TransactionMeta.key == 'some_key',
            TransactionMeta.value == 'some value'
        )
    )
)
```
