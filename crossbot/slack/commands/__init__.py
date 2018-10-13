# from https://stackoverflow.com/a/3365846
import importlib
import pkgutil


COMMANDS = []
for _, module_name, _ in  pkgutil.walk_packages(__path__):
    module_full_name = __name__ + '.' + module_name
    importlib.import_module(module_full_name)
    COMMANDS.append(module_name)
