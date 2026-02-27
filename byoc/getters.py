from typing import Callable, Any, Iterable
from .configs import Config
from .apply import Pipeline
from .utils import identity
from dataclasses import dataclass

class Getter:
    """
    Base class for objects that retrieve configuration values.

    Each getter describes how to retrieve possible configuration values for a 
    parameter.  When defining a parameter, 

    Getter objects are meant to be passed to `param`, where they specify the 
    order in which specific configuration values are to be retrieved.  Each 
    getter object can retrieve values in any way it sees fit.  The getters 
    provided by BYOC—`Key`, `Method`, `Func`, and `Value`—should cover the vast 
    majority of use-cases, but it's also possible to create custom getters.

    The getter API is just one method: `iter_values`.  This method is called 
    during `load` and should yield any values appropriate for the application 
    and config objects being loaded, along with the corresponding metadata.  
    Typically, additional information about the values to retrieve will be 
    provided when the getter is instantiated, but this isn't part of the API.
    """

    def iter_values(self, app: Any, configs: list[Config]) -> Iterable[tuple[Any, Any]]:
        """
        Yield the values retrieved by this getter.

        Arguments:
            app: The object being loaded.
            configs: The list of `Config` objects being used to load the app.

        Return:
            An iterable of (value, meta) tuples.

        This method is typically implemented as a generator, but any kind of 
        iterable return value is supported.
        """
        raise NotImplementedError

class Key(Getter):
    """
    Lookup specific values in the data structures loaded by `Config` objects.

    Arguments:

        config_cls:
            A `Config` class.  Only configs of this class (subclasses included) 
            will be searched for values.  

        key:

        apply:
            One or more functions used to transform the values produced by this 
            getter.  See :paramref:`param.apply` for details.

    This is the most commonly used getter.  Broadly speaking, it requires two 
    pieces of information: (i) the set of configs to search, and (ii) the key 
    to look up in each config.  

    The basic idea is to specify (i) a 
    group of configs to check and (ii) 
    """

    def __init__(self, config_cls: type[Config], key: Any, *, apply=identity):
        self.config_cls = config_cls
        self.key = key
        self.apply = Pipeline(apply)

    def iter_values(self, app, configs):
        for config in configs:
            if not isinstance(config, self.config_cls):
                continue

            for finder in config.iter_finders():
                for value, meta in finder.iter_values(app, self.key):
                    yield self.apply(value, app=app, meta=meta), meta

class Method(Getter):

    def __init__(self, method):
        self.method = method
        self.meta = _get_python_meta()

    def iter_values(self, app, configs):
        yield self.method(app), self.meta

class Func(Getter):

    def __init__(self, func: Callable[[], Any]):
        self.func = func
        self.meta = _get_python_meta()

    def iter_values(self, app: Any, configs: list[Config]):
        yield self.func(), self.meta

class Value(Getter):

    def __init__(self, value):
        self.value = value
        self.meta = _get_python_meta()

    def iter_values(self, app, configs):
        yield self.value, self.meta

@dataclass
class PythonMeta:
    file: str
    line: int

def _get_python_meta():
    """
    Return the file and line number where `Method`, `Func`, or `Value` was 
    called from.

    This function is designed to work when called from the constructors of the 
    above classes.
    """
    import inspect

    local_frame = inspect.currentframe()
    try:
        if local_frame is None:
            return

        caller_frame = local_frame.f_back.f_back
        try:
            return PythonMeta(
                    caller_frame.f_code.co_filename,
                    caller_frame.f_lineno,
            )
        finally:
            del caller_frame

    finally:
        del local_frame


