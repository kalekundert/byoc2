from .params import param
from .errors import UsageError
from itertools import chain
from functools import partial
from collections.abc import MutableSequence, MutableMapping, Iterable
from operator import setitem

from typing import Any, Optional
from .configs import Config

class Loader:

    def __init__(self, attrs, configs):
        self._attributes = []
        self._attribute_values = {}
        self._attribute_locks = {}
        self._configs = configs
        self._is_loading = False

        self.add_attributes(attrs)

    def load(self):
        self._is_loading = True

        try:
            for param in _iter_unique_params(self._attributes):
                param.begin_load(self)

            # Allow each config to load itself in a context without any 
            # upstream configs.  This allows command-line argument parsers to 
            # display config-aware default values.

            for config in self._configs:
                self._attribute_values = {}
                config.load()

            self._attribute_values = {}

            for attr in self._attributes:
                app = attr.app
                param = attr.param
                setter = attr.setter

                value = self.get_attribute_value(app, param)
                setter(value)

        finally:
            for param in _iter_unique_params(self._attributes):
                param.end_load()

    def add_attributes(self, attrs):
        if self._is_loading:
            for param in _iter_unique_params(attrs, exclude=self._attributes):
                param.begin_load(self)

        self._attributes += attrs

    def get_attribute_value(self, app, param):
        k = id(app), id(param)

        if k in self._attribute_locks:
            err = UsageError("encountered circular dependency while loading the following parameters:")
            err.info += [
                    repr(param)
                    for app, param in chain(
                        self._attribute_locks.values(),
                        [(app, param)],
                    )
            ]
            raise err

        if k not in self._attribute_values:
            self._attribute_locks[k] = (app, param)
            self._attribute_values[k] = param.load_value(app, self._configs)
            del self._attribute_locks[k]

        return self._attribute_values[k]

class PendingAttribute:

    def __init__(self, app, param, setter):
        self.app = app
        self.param = param
        self.setter = setter

    def __repr__(self):
        return f'<PendingAttribute app={self.app} param={self.param}>'

def load(
        app: Any,
        *,
        configs: Optional[Iterable[Config]] = None,
):
    params = _find_params_in_obj(app)
    configs = _find_configs_in_obj(app) if configs is None else configs
    attrs = [
            PendingAttribute(app, param, setter)
            for param, setter in params
    ]
    loader = Loader(attrs, configs)
    loader.load()

def load_collection(
        app: Any,
        configs: Iterable[Config],
):
    params = _find_params_in_collection(app)

    attrs = [
            PendingAttribute(app, param, setter)
            for param, setter in params
    ]
    loader = Loader(attrs, configs)
    loader.load()

def recursive_load(loader, task, app):
    params = _find_params_in_obj(app)
    attrs = [
            PendingAttribute(app, param, setter)
            for param, setter in params
    ]
    loader.add_attributes(attrs)

def recursive_load_from_list(loader, task, apps):
    for app in apps:
        recursive_load(loader, task, app)

def recursive_load_from_dict_values(loader, task, apps):
    for app in apps.values():
        recursive_load(loader, task, app)


def _find_params_in_obj(app):
    params = _find_cls_attrs(
            app,
            lambda k, v: isinstance(v, param)
    )
    return [
            (v, partial(setattr, app, k))
            for k, v in params.items()
    ]

def _find_params_in_collection(app):
    if not isinstance(app, (MutableSequence, MutableMapping)):
        raise UsageError(f"expected list or dict, not {app!r}")

    return list(_iter_params_in_collection_item(None, None, app))

def _iter_params_in_collection_item(collection, key, item):
    if isinstance(item, param):
        yield item, partial(setitem, collection, key)

    elif isinstance(item, MutableSequence):
        for i, x in enumerate(item):
            yield from _iter_params_in_collection_item(item, i, x)

    elif isinstance(item, MutableMapping):
        for k, v in item.items():
            yield from _iter_params_in_collection_item(item, k, v)

    else:
        pass

def _find_configs_in_obj(app):
    config_factories = _find_cls_attrs(
            app,
            lambda k, v: getattr(v, '_byoc_is_config_factory', False)
    )
    configs = chain.from_iterable(
            f(app) for f in config_factories.values()
    )
    return list(configs)

def _find_meta_in_obj(app):
    pass

def _iter_unique_params(attrs, exclude=None):
    new_params = set(attr.param for attr in attrs)
    old_params = set(attr.param for attr in exclude) if exclude else set()
    yield from new_params - old_params

def _find_cls_attrs(obj, predicate=lambda k, v: True):
    cls_attrs = {}
    defined_keys = set(obj.__dict__)

    for cls in obj.__class__.__mro__:
        for k, v in cls.__dict__.items():
            if k in defined_keys:
                continue
            defined_keys.add(k)

            if predicate(k, v):
                cls_attrs[k] = v

    return cls_attrs
