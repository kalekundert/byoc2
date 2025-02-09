from typing import Callable, Any
from .configs import Config
from .cast import CastFuncs
from .utils import identity
from dataclasses import dataclass

class Getter:

    def iter_values(self, app, configs):
        """
        Yield (value, meta) tuples.
        """
        raise NotImplementedError

class Key(Getter):

    def __init__(self, config_cls, key, *, cast=identity):
        self.config_cls = config_cls
        self.key = key
        self.cast = CastFuncs(cast)

    def iter_values(self, app, configs):
        for config in configs:
            if not isinstance(config, self.config_cls):
                continue

            for finder in config.iter_finders():
                for value, meta in finder.iter_values(app, self.key):
                    yield self.cast(value, app=app, meta=meta), meta

class Method(Getter):

    def __init__(self, method):
        self.method = method
        self.meta = _get_source_meta()

    def iter_values(self, app, configs):
        yield self.method(app), self.meta

class Func(Getter):

    def __init__(self, func: Callable[[], Any]):
        self.func = func
        self.meta = _get_source_meta()

    def iter_values(self, app: Any, configs: list[Config]):
        yield self.func(), self.meta

class Value(Getter):

    def __init__(self, value):
        self.value = value
        self.meta = _get_source_meta()

    def iter_values(self, app, configs):
        yield self.value, self.meta

@dataclass
class SourceMeta:
    file: str
    line: int

def _get_source_meta():
    import inspect

    local_frame = inspect.currentframe()
    try:
        if local_frame is None:
            return

        caller_frame = local_frame.f_back.f_back
        try:
            return SourceMeta(
                    caller_frame.f_code.co_filename,
                    caller_frame.f_lineno,
            )
        finally:
            del caller_frame

    finally:
        del local_frame


