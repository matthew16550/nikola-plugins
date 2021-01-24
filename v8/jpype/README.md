This plugin makes [JPype](https://jpype.readthedocs.io/) available for use by other plugins.

See the [plantuml](https://plugins.getnikola.com/#plantuml) plugin for example usage.

Plugins using JPype should do something like below to start the JVM before any Java imports. But do it as late as
possible (after `set_site()`) because the JVM is slow to start so should only be used when necessary.

```python
plugin_info = site.plugin_manager.getPluginByName('jpype', category='ConfigPlugin')
if not plugin_info:
    req_missing("jpype plugin", "use ...", python=False)
plugin_info.plugin_object.ensure_jvm_started()
```
