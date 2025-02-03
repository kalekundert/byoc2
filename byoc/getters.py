from typing import Callable, Any
from .configs.configs import Config

class Getter:

    def iter_values(self, app, configs):
        raise NotImplementedError

class Key(Getter):

    def __init__(self, config_cls, key):
        self.config_cls = config_cls
        self.key = key

    def iter_values(self, app, configs):
        for config in configs:
            if not isinstance(config, self.config_cls):
                continue

            for layer in config.iter_cached_layers():
                try:
                    yield layer.payload[self.key]
                except KeyError:
                    pass


class Method(Getter):

    def __init__(self, method):
        self.method = method

    def iter_values(self, app, configs):
        yield self.method(app)

class Func(Getter):

    def __init__(self, func: Callable[[], Any]):
        self.func = func

    def iter_values(self, app: Any, configs: list[Config]):
        yield self.func()

class Value(Getter):

    def __init__(self, value):
        self.value = value

    def iter_values(self, app, configs):
        yield self.value
