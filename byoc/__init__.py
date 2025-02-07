"Build your own config."

# Define the public API
_pre_import_keys = set()
_pre_import_keys |= set(globals())

from .load import (
        Loader, PendingAttribute, load, load_collection, recursive_load,
        recursive_load_from_list, recursive_load_from_dict_values,
)
from .params.param import param, getitem
from .params.config_attr import config_attr, ConfigAttr
from .getters import Getter, Key, Method, Func, Value
from .cast import arithmetic_eval, int_eval, float_eval
from .pick import ValuesIter, first
from .configs.config import Config, configs
from .configs.environment import EnvironmentConfig
from .configs.cli import CliConfig, ArgparseConfig, DocoptConfig, mako_usage
from .configs.files import FileConfig, JsonConfig, NtConfig, TomlConfig, YamlConfig
from .configs.finders import Finder, DictFinder
from .utils import identity, lookup
from .errors import UsageError, NoValueFound

# Make everything imported above appear to come from this module:
_post_import_keys = set(globals())
for _key in _post_import_keys - _pre_import_keys:
    globals()[_key].__module__ = 'byoc'
del _pre_import_keys, _post_import_keys, _key

__version__ = '0.0.0'

