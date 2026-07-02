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

The sections below are rendered from each plugin's module documentation, so
they always match the installed version.

## Activity

::: sqlalchemy_continuum.plugins.activity
    options:
      members: false
      show_root_heading: false
      show_root_toc_entry: false

## Flask

::: sqlalchemy_continuum.plugins.flask
    options:
      members: false
      show_root_heading: false
      show_root_toc_entry: false

## PropertyModTracker

::: sqlalchemy_continuum.plugins.property_mod_tracker
    options:
      members: false
      show_root_heading: false
      show_root_toc_entry: false

## TransactionChanges

::: sqlalchemy_continuum.plugins.transaction_changes
    options:
      members: false
      show_root_heading: false
      show_root_toc_entry: false

## TransactionMeta

::: sqlalchemy_continuum.plugins.transaction_meta
    options:
      members: false
      show_root_heading: false
      show_root_toc_entry: false
