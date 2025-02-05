from .pick import ValuesIter, first
from .utils import identity
from .errors import UsageError

class param:
    
    def __init__(
            self,
            *getters,
            pick=first,
            cast=identity,
            on_load=None,
    ):
        self.getters = getters
        self.cast = cast
        self.pick = pick
        self.on_load = on_load

        self.app_name = None
        self.name = None

        self._loader = None

    def __repr__(self):
        if self.app_name is None:
            return f'<param {self.name}>'
        else:
            return f'<param {self.app_name}.{self.name}>'

    def __get__(self, app, cls=None):
        return self.get_value(app)

    def __set_name__(self, owner, name):
        self.app_name = owner.__name__ if owner is not None else None
        self.name = name

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    def begin_load(self, loader):
        if self._loader is not None:
            raise UsageError(f"{param} is already being loaded by {self.loader}; cannot begin loading with {loader}")
        self._loader = loader

    def end_load(self):
        self._require_active_loader()
        self._loader = None

    def get_value(self, app):
        self._require_active_loader()
        return self._loader.get_attribute_value(app, self)

    def load_value(self, app, configs):
        self._require_active_loader()

        values = ValuesIter(self, self._iter_values(app, configs))
        value = self.pick(values)

        if self.on_load is not None:
            self.on_load(self._loader, app, value)

        return self.cast(value)

    def _iter_values(self, app, configs):
        for getter in self.getters:
            yield from getter.iter_values(app, configs)

    def _require_active_loader(self):
        if self._loader is None:
            raise UsageError(f"cannot use {self} outside of `byoc.load()`")

def getitem(app, key):
    value = app[key]

    if isinstance(value, param):
        return param.get_value(app)
    else:
        return value

