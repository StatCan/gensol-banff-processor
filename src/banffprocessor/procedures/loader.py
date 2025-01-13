"""Load plugin files from a defined location as python modules."""
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from banffprocessor.nls import _
from banffprocessor.procedures import factory

# Module name to register user plugins under
_USER_MODULE_NAME = "plugins"

def load_plugins(plugin_dir: str | Path) -> None:
    """Load plugins from the plugin directory.

    Load all python files that include a register function from `plugin_dir`
    as modules and call these register functions to load plugin classes.

    :param plugin_dir: The directory where the plugin files to load are located
    :type plugin_dir: str | Path
    :raises ValueError: If `plugin_dir` is an empty string or None
    """
    if(not plugin_dir):
        msg = _("plugin_dir argument was empty or None.")
        raise ValueError(msg)

    plugin_dir = Path(plugin_dir)

    # Get a list of all the modules in the specified folder, non recursively
    module_files = plugin_dir.resolve().glob("*.py")
    for file in module_files:
        if(file.is_file() and not file.name.startswith("_")):
            # Module name is just filename without extension
            module_name = f"{_USER_MODULE_NAME}.{file.stem}"

            spec = spec_from_file_location(module_name, file)

            plugin = module_from_spec(spec)
            sys.modules[module_name] = plugin
            spec.loader.exec_module(plugin)
            if(hasattr(plugin, "register")):
                plugin.register(factory)
