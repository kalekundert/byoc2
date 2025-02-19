import smartcall

from ..apply import Pipeline
from ..pick import ValuesIter, first
from ..utils import identity
from ..errors import UsageError
from smartcall import PosOrKw, KwOnly

class param:
    """
    Describe how to load a value from multiple possible configuration sources.

    Arguments:
        getters:

        apply:

        pick:

        on_load:

    .. autoclasstoc::
    """
    
    def __init__(
            self,
            *getters,
            apply=identity,
            pick=first,
            on_load=None,
    ):
        self.getters = getters
        self.apply = Pipeline(apply)
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
        """
        Begin loading this parameter.

        Arguments:
            loader:
                The `Loader` object that will be responsible for calculating 
                and storing values for this parameter.  Each parameter can only 
                be in use by one loader at a time.

        This method is meant for internal use within `Loader`.  Calling this 
        method externally would risk breaking some internal invariants and 
        sanity checks.
        """
        if self._loader is not None and self._loader is not loader:
            raise UsageError(f"{param} is already being loaded by {self.loader}; cannot begin loading with {loader}")

        self._loader = loader
        self._begin_count += 1

    def end_load(self):
        """
        Indicate that this parameter is no longer being loaded.

        This method is meant for internal use within `Loader`.  Calling this 
        method externally would risk breaking some internal invariants and 
        sanity checks.
        """
        self._require_active_loader()

        self._begin_count -= 1
        if self._begin_count == 0:
            self._loader = None

    def get_value(self, app):
        """
        Return the value of this parameter for the given app.

        Arguments:
            app:
                The object that this parameter belongs to.  Parameters can 
                belong to multiple apps, e.g. if the parameter is a class 
                attribute and the apps are instances of that class, so this 
                argument gives us the right app to work with.

        This method is a thin wrapper around `Loader.load_attribute_value`.  
        Refer there for more information about what exactly this function does 
        and when it should be used.
        """
        self._require_active_loader()
        return self._loader.load_attribute_value(app, self)

    def load_value(self, app, configs):
        """
        Calculate a value for this parameter.

        Arguments:
            app:
                See `get_value`.

            configs:
                The list of configuration sources to use.  Be aware that this 
                method can be called multiple times with different sets of 
                configuration sources during a single loading process.

        This method is meant for internal use within `Loader`.  I cannot think 
        of any other scenario where it would be appropriate to use this method.  
        Use `get_value` if you want to manually calculate a value for a 
        parameter.  That will end up calling this method, while also allowing 
        the loader to do the necessary bookkeeping.
        """
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
                value = self.apply(value, app=app, meta=meta)
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

