"Build your own config."

# Define the public API
_pre_import_keys = set()
_pre_import_keys |= set(globals())

from .load import (
        Loader, Task, load, load_collection, recursive_load,
        recursive_load_from_list, recursive_load_from_dict_values,
)
from .params import param
from .getters import Getter, Key, Method, Func, Value
from .pick import ValuesIter, first
from .configs.configs import Config, DocoptConfig, TomlConfig, configs
from .configs.layers import Layer
from .errors import UsageError, CircularDependency, NotYetAvailable, NoValueFound

# Make everything imported above appear to come from this module:
_post_import_keys = set(globals())
for _key in _post_import_keys - _pre_import_keys:
    globals()[_key].__module__ = 'byoc'
del _pre_import_keys, _post_import_keys, _key

__version__ = '0.0.0'

