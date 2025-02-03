from .pick import ValuesIter, first
from .utils import identity
from .errors import NotYetAvailable

class param:
    
    def __init__(
            self,
            *getters,
            priority=0,
            pick=first,
            cast=identity,
            on_load=None,
    ):
        self.getters = getters
        self.cast = cast
        self.pick = pick
        self.priority = priority
        self.on_load = on_load

        self.app_name = None
        self.name = None

    def __repr__(self):
        if self.app_name is None:
            return f'<param {self.name}>'
        else:
            return f'<param {self.app_name}.{self.name}>'

    def __get__(self, app, cls=None):
        raise NotYetAvailable(self)

    def __set_name__(self, owner, name):
        self.app_name = owner.__name__ if owner is not None else None
        self.name = name

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    def get_value(self, app, configs):
        values = ValuesIter(self, self._iter_values(app, configs))
        value = self.pick(values)
        return self.cast(value)

    def _iter_values(self, app, configs):
        for getter in self.getters:
            yield from getter.iter_values(app, configs)


