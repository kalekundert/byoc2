import networkx as nx

from .params import NotYetAvailable, param
from .errors import UsageError, CircularDependency
from heapq import heappush, heappop
from itertools import chain
from functools import partial, total_ordering
from collections.abc import MutableSequence, MutableMapping, Iterable
from operator import setitem

from typing import Any, Optional
from .configs import Config

class Loader:

    def __init__(self):
        self.queue = []
        self.dependencies = nx.DiGraph()

    def load(self):
        while self.queue:
            task = heappop(self.queue)

            app = task.app
            param = task.param
            configs = task.configs
            setter = task.setter

            try:
                value = param.get_value(app, configs)

            except NotYetAvailable as err:
                if _is_circular_dependency(self.dependencies, err.param, param):
                    raise CircularDependency(param, err.param)

                self.dependencies.add_edge(param, err.param)
                task.num_dependencies += 1
                heappush(self.queue, task)
            
            else:
                setter(value)
                if param.on_load:
                    param.on_load(self, task, value)

    def push(self, tasks):
        for i, task in enumerate(tasks):
            task.push_order = i
            heappush(self.queue, task)

@total_ordering
class Task:

    def __init__(self, app, param, setter, configs):
        self.app = app
        self.param = param
        self.setter = setter
        self.configs = configs
        self.num_dependencies = 0
        self.push_order = None

    def __repr__(self):
        return f'<Task {self.param}>'

    def __eq__(self, other):
        return self._sort_key == other._sort_key

    def __lt__(self, other):
        return self._sort_key < other._sort_key

    @property
    def _sort_key(self):
        return self.num_dependencies, -self.param.priority, self.push_order


def load(
        app: Any,
        *,
        configs: Optional[Iterable[Config]] = None,
):
    params = _find_params_in_obj(app)
    configs = _find_configs_in_obj(app) if configs is None else configs

    loader = Loader()
    tasks = [
            Task(app, param, setter, configs)
            for param, setter in params
    ]
    loader.push(tasks)
    loader.load()

def load_collection(
        app: Any,
        configs: Iterable[Config],
):
    params = _find_params_in_collection(app)

    loader = Loader()
    tasks = [
            Task(app, param, setter, configs)
            for param, setter in params
    ]
    loader.push(tasks)
    loader.load()

def recursive_load(loader, task, app):
    params = _find_params_in_obj(app)
    configs = _find_configs_in_obj(app) + task.configs
    tasks = [
            Task(app, param, setter, configs)
            for param, setter in params
    ]
    loader.push(tasks)

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

def _is_circular_dependency(G, a, b):
    if not G.has_node(a):
        return False
    if not G.has_node(b):
        return False
    
    return nx.has_path(G, b, a)

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
