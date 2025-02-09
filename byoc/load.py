from .params.param import param
from .utils import do_nothing
from .errors import UsageError
from itertools import chain
from functools import partial
from collections.abc import MutableSequence, MutableMapping, Iterable
from more_itertools import one, value_chain
from operator import setitem

from typing import Any, Optional
from .configs import Config

class Loader:

    def __init__(self, attrs, configs):
        self._attributes = {}
        self._locked_keys = []
        self._loaded_keys = set()
        self._pending_keys = []
        self._mid_load_keys = set()
        self._configs = configs
        self._loaded_configs = []
        self._is_loading = False

        self.add_attributes(attrs)

    def load(self):
        self._is_loading = True

        try:
            for attr in self._attributes.values():
                attr.param.begin_load(self)

            # Allow each config to load itself in a context without any 
            # upstream configs.  One important use-case for this feature is to 
            # allow command-line argument parsers to display usage text with 
            # config-aware default values.

            self._loaded_configs = []

            for config in self._configs:
                self._reset_attributes()
                config.load()
                self._loaded_configs.append(config)

            self._reset_attributes()

            while self._pending_keys:
                k = self._pending_keys[0]
                attr = self._attributes[k]
                self.load_attribute_value(attr.app, attr.param)

        finally:
            for attr in self._attributes.values():
                attr.param.end_load()

    def add_attributes(self, attrs):
        for attr in attrs:
            k = _key_from_attr(attr)
            if k in self._attributes:
                err = UsageError("cannot load the same attribute twice")
                err.info += f"app: {attr.app!r}"
                err.info += f"param: {attr.param!r}"
                raise err

            self._attributes[k] = attr
            self._pending_keys.append(k)

        if self._is_loading:
            for attr in attrs:
                attr.param.begin_load(self)

            self._mid_load_keys |= {_key_from_attr(attr) for attr in attrs}

    def load_attribute_value(self, app, param):
        k = _key_from_app_param(app, param)

        if k not in self._attributes:
            err = UsageError("cannot load unknown attribute")
            err.info += f"app: {app!r}"
            err.info += f"param: {param!r}"
            raise err

        attr = self._attributes[k]
        app, param = attr.app, attr.param

        if k in self._loaded_keys:
            err = UsageError("attribute already loaded")
            err.info += f"app: {app!r}"
            err.info += f"param: {param!r}"
            raise err

        assert k in self._pending_keys

        if k in self._locked_keys:
            err = UsageError("encountered circular dependency while loading the following parameters:")
            err.info += [
                    repr(attr)
                    for attr in value_chain(
                        (self._attributes[k] for k in self._locked_keys),
                        attr,
                    )
            ]
            raise err

        self._locked_keys.append(k)
        try:
            value, meta = param.load_value(app, self._loaded_configs)
        finally:
            self._locked_keys.pop()

        attr.set_attr(value)
        attr.set_meta(meta)

        self._loaded_keys.add(k)
        self._pending_keys.remove(k)
        
        return value

    def _reset_attributes(self):
        assert not self._locked_keys

        for k in self._loaded_keys:
            attr = self._attributes[k]
            attr.del_attr()
            attr.del_meta()

        for k in self._mid_load_keys:
            attr = self._attributes.pop(k)
            attr.param.end_load()

        self._mid_load_keys = set()
        self._loaded_keys = set()
        self._pending_keys = list(self._attributes)

class PendingAttribute:

    def __init__(
            self, *,
            app, meta, param,
            set_attr, del_attr,
            set_meta, del_meta,
    ):
        self.app = app
        self.meta = meta
        self.param = param
        self.set_attr, self.del_attr = set_attr, del_attr
        self.set_meta, self.del_meta = set_meta, del_meta

    def __repr__(self):
        return f'<PendingAttribute app={self.app} param={self.param}>'

def load(
        app: Any,
        *,
        configs: Optional[Iterable[Config]] = None,
        meta: Optional[Any] = None,
):
    configs = _find_configs_in_obj(app) if configs is None else configs
    meta = _find_meta_in_obj(app) if meta is None else meta
    attrs = _find_attrs_in_obj(app, meta)

    loader = Loader(attrs, configs)
    loader.load()

def load_collection(
        app: Any,
        configs: Iterable[Config],
        *,
        meta: Optional[Any] = None,
):
    attrs = _find_attrs_in_collection(app, meta)

    loader = Loader(attrs, configs)
    loader.load()

def recursive_load(loader, app):
    meta = _find_meta_in_obj(app)
    attrs = _find_attrs_in_obj(app, meta)
    loader.add_attributes(attrs)

def recursive_load_from_list(loader, apps):
    for app in apps:
        recursive_load(loader, app)

def recursive_load_from_dict_values(loader, apps):
    for app in apps.values():
        recursive_load(loader, app)

def configs(method):
    method._byoc_is_config_factory = True
    return method

def meta(method):
    method._byoc_is_meta_factory = True
    return method


def _find_attrs_in_obj(app, meta):
    params = _find_cls_attrs(
            app,
            lambda k, v: isinstance(v, param)
    )
    return [
            PendingAttribute(
                app=app,
                meta=meta,
                param=v,
                set_attr=partial(setattr, app, k),
                del_attr=partial(delattr, app, k),
                set_meta=partial(setattr, meta, k) \
                        if meta is not None else do_nothing,
                del_meta=partial(delattr, meta, k) \
                        if meta is not None else do_nothing,
            )
            for k, v in params.items()
    ]

def _find_attrs_in_collection(app, meta):
    if not isinstance(app, (MutableSequence, MutableMapping)):
        raise UsageError(f"expected list or dict, not {app!r}")

    # Note that we wrap the app in a list to get the recursive algorithm 
    # started.  If the app were a parameter, this would produce unexpected 
    # results: the setters would modify this temporary list instead of anything 
    # visible to the user.  However, because we check that the app is actually 
    # a collection above, this cannot happen.

    return list(_iter_attrs_in_collection(app, meta, [app], [meta], 0))

def _iter_attrs_in_collection(app, meta, app_collection, meta_collection, key):
    app_item = app_collection[key]
    meta_item = meta_collection[key] if meta_collection is not None else None

    if isinstance(app_item, param):
        yield PendingAttribute(
                app=app,
                meta=meta,
                param=app_item,
                set_attr=partial(setitem, app_collection, key),
                del_attr=partial(setitem, app_collection, key, app_item),
                set_meta=partial(setitem, meta_collection, key) \
                        if meta_collection is not None else do_nothing,
                del_meta=partial(setitem, meta_collection, key, None) \
                        if meta_collection is not None else do_nothing,
        )

    elif isinstance(app_item, MutableSequence):
        for i, _ in enumerate(app_item):
            yield from _iter_attrs_in_collection(
                    app, meta, app_item, meta_item, i)

    elif isinstance(app_item, MutableMapping):
        for k in app_item:
            yield from _iter_attrs_in_collection(
                    app, meta, app_item, meta_item, k)

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
    meta_factories = _find_cls_attrs(
            app,
            lambda k, v: getattr(v, '_byoc_is_meta_factory', False)
    )

    if not meta_factories:
        return None

    if len(meta_factories) > 1:
        err = UsageError("cannot mark more than one method with `@byoc.meta`")
        err.info += "found the following marked methods:\n" + '\n'.join(meta_factories)
        raise err

    meta_factory = one(
            meta_factories.values(),
            too_short=AssertionError,
            too_long=AssertionError,
    )
    return meta_factory(app)

def _key_from_attr(attr):
    return _key_from_app_param(attr.app, attr.param)

def _key_from_app_param(app, param):
    return id(app), id(param)

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
