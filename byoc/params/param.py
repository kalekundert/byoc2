import smartcall

from ..cast import CastFuncs
from ..pick import ValuesIter, first
from ..utils import identity
from ..errors import UsageError
from smartcall import PosOrKw, KwOnly

class param:
    
    def __init__(
            self,
            *getters,
            pick=first,
            cast=identity,
            on_load=None,
    ):
        self.getters = getters
        self.cast = CastFuncs(cast)
        self.pick = pick
        self.on_load = on_load

        self.app_name = None
        self.name = None

        self._loader = None
        self._begin_count = 0

    def __repr__(self):
        if self.app_name is None:
            return f'<param {self.name}>'
        else:
            return f'<param {self.app_name}.{self.name}>'

    def __get__(self, app, cls=None):
        if self._loader is None:
            err = UsageError("parameter has no value")
            err.blame += "Did you forget to call `byoc.load()`?"
            raise err

        return self.get_value(app)

    def __set_name__(self, owner, name):
        self.app_name = owner.__name__ if owner is not None else None
        self.name = name

    def begin_load(self, loader):
        if self._loader is not None and self._loader is not loader:
            raise UsageError(f"{param} is already being loaded by {self.loader}; cannot begin loading with {loader}")

        self._loader = loader
        self._begin_count += 1

    def end_load(self):
        self._require_active_loader()

        self._begin_count -= 1
        if self._begin_count == 0:
            self._loader = None

    def get_value(self, app):
        self._require_active_loader()
        return self._loader.load_attribute_value(app, self)

    def load_value(self, app, configs):
        self._require_active_loader()

        values_iter = ValuesIter(self, self._iter_values(app, configs))
        value = self.pick(values_iter)
        meta = values_iter.meta

        if self.on_load is not None:
            smartcall.call(
                    self.on_load,
                    PosOrKw(loader=self._loader),
                    PosOrKw(value=value),
                    KwOnly(meta=meta),
                    KwOnly(app=app),
            )

        return value, meta

    def _iter_values(self, app, configs):
        for getter in self.getters:
            for value, meta in getter.iter_values(app, configs):
                value = self.cast(value, app=app, meta=meta)
                yield value, meta

    def _require_active_loader(self):
        if self._loader is None:
            raise UsageError(f"cannot use {self} outside of `byoc.load()`")

def getitem(app, key):
    value = app[key]

    if isinstance(value, param):
        return param.get_value(app)
    else:
        return value

