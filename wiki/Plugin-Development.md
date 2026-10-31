# Plugin Development

NeoArch plugins are Python modules that extend the GUI. This page is a short
overview — the full guide lives with the plugin catalogue:
[community_plugins/README.md](https://github.com/sanjayadanushka712/NeoArch/blob/main/community_plugins/README.md).

## Quick route — the built-in creator

1. Open NeoArch → **Plugins** → **Community Plugins**.
2. Click **Create Plugin** and fill in the details.
3. Edit the generated template and restart NeoArch.

## Plugin structure

A plugin is a single Python file that exposes a hook:

```python
"""
My Plugin
Short description shown in the plugin list
"""

from neoarch.managers.plugin_manager import PluginManager


class MyPlugin:
    name = "My Plugin"
    version = "1.0.0"
    description = "What the plugin does"

    def activate(self):
        """Called when the plugin is enabled."""

    def deactivate(self):
        """Called when the plugin is disabled."""


def register():
    return MyPlugin
```

## Publishing to the community catalogue

1. Add your plugin folder under `community_plugins/`.
2. Register it in `community_plugins/index.json` (name, version, description,
   author, entry point).
3. Open a pull request against `dev` — the catalogue is reviewed before merge.

## Guidelines

- Plugins must not block the UI thread; use the worker helpers for any
  subprocess work.
- Never write to the package database directly — go through the package
  services so transactions, logging, and privilege escalation stay correct.
- Declare the package sources a plugin touches in its description so users
  know what it does.

## See also

- [Plugins](Plugins.md)
- [Architecture](Architecture.md)
