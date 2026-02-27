from __future__ import annotations

import smartcall

from ..apply import Pipeline
from ..pick import ValuesIter, first
from ..utils import identity
from ..errors import UsageError
from smartcall import PosOrKw, KwOnly

from typing import Iterable, Optional, Any, Callable

class param:
    """
    Specify how to load a value from multiple possible configuration sources.

    Arguments:
        getters:
            Any number of `Getter` objects.  Each getter specifies a different 
            way to generate one or more values for this parameter.  The 
            :paramref:`pick` argument determines which of these values are  
            actually used.

            The most commonly-used getter is `Key`, which is used to look up 
            values from `Config` objects.  Also important are `Value`, `Func`, 
            and `Method`, which are used to calculate values directly from 
            python.  If necessary, you can also write your own `Getter` 
            subclasses.

        apply:
            One or more functions used to transform the values produced by 
            the above getters.  If multiple functions are given, they are 
            called in order, with the output from the previous being the input 
            to the next.

            Each function must accept a single positional argument, which will 
            be the value to transform.  The functions may also accept any of 
            the following optional keyword arguments, to get additional 
            information about the value being transformed:

            - *app*: The object that this parameter belongs to.
            - *meta*: An object describing where this value came from, e.g.  
              `CliMeta`, `FileMeta`, etc.  For example, the `relpath` apply 
              function uses this information to interpret paths relative to the 
              file they were read from.

            The `Key` getter also accepts an :paramref:`~Key.apply` argument, 
            for cases where you transform values loaded from different 
            configuration sources in different ways.

        pick:
            The function that will be used to choose a final value for this 
            parameter, given all of the values produced by the above getters.  
            The default is `first`, which simply uses the first value found.  
            Other common choices are :func:`~byoc.list` and `merge_dicts`.

            This function should accept one argument: an iterable over the 
            values produced by the getters.  The actual iterable that BYOC 
            passes to this function is a `ValuesIter` object.  This object 
            invokes the getters on-demand, so any values that are not needed 
            (e.g. the second, if you are only using the first) are never 
            generated.  It's possible that looking up a value could be 
            expensive, so this ensures that lookups only happen when the value 
            might be used.

            One important responsibility of the pick function is to preserve 
            the metadata associated with each value.  That is, to produce a 
            single metadata object that completely describes all of the picked 
            values.  Generally, this is done by having the structure of the 
            metadata match the structure of the picked value itself.  For 
            example, if a single value is picked, that value's metadata is used 
            directly.  If a list of values are picked, those values' metadata 
            are likewise combined into a list.

            The metadata is made available to the pick function via 
            aforementioned `ValuesIter` object.  If you treat this object like 
            a normal iterator, it will simply iterate over the relevant values.  
            This allows the use of metadata-unaware pick functions, if you 
            don't mind losing the metadata.  However, the `ValuesIter` object 
            also has:

            - A `with_meta` property that iterates simultaneously over the 
              relevant values and their corresponding metadata.
            - A :attr:`~ValuesIter.meta` attribute that can be set to the 
              metadata of the picked value.

            These features make it possible for the pick function to preserve 
            metadata.  All of the built-in pick functions do this.  If you're 
            writing a custom pick function, of course, you only need to worry 
            about this if you'll be using the metadata for something.  See 
            `ValuesIter` for more details.

        on_load:
            A function to call after a final value has been picked.  The 
            primary use case is to register additional objects to load, i.e.  
            with `recursive_load`.  This function can accept up to four 
            arguments, all optional:

            - *loader* (positional or keyword): The `Loader` object being used 
              to load this parameter.

            - *value* (positional or keyword): The final value that was picked 
              for this parameter.

            - *meta* (keyword only): The metadata associated with the picked 
              value.

            - *app* (keyword only): The object that this parameter belongs to.

    .. autoclasstoc::

    The most common way to create parameters is as class attributes, i.e. in 
    the manner expected by `load`.  The advantage of this approach is that it 
    allows you, during the loading process, to access other parameters using 
    the normal attribute access syntax.  If the other parameter has already 
    been loaded, this will simply retrieve its value.  If not, this will load 
    the other parameter right then, and return its value.  This syntax works 
    because `param` objects are `descriptors <descriptor>`, so they can control 
    what happens when attribute access is attempted.

    Parameters can also be used as standalone objects, via `load_collection` or 
    `Loader`.  In these cases, you have to be more careful when accessing other 
    parameters during the loading process, to check whether you're getting the 
    value or the parameter object itself.  Functions like `getitem` can help 
    with this.

    Example:

        A parameter that can load values from the command line, an environment 
        variable, and a default value:

        .. tab:: app.py

            .. code-block:: python

                import byoc
                from byoc import Key, Value, ArgparseConfig, EnvVarConfig

                class App:
                    x = byoc.param(
                            Key(ArgparseConfig, 'x'),
                            Key(EnvVarConfig, 'MY_APP_X', apply=int),
                            Value(0),
                    )

                    @byoc.configs
                    def iter_configs(self):
                        yield ArgparseConfig(self.get_argparser)
                        yield EnvVarConfig()

                    def get_argparser(self):
                        import argparse
                        parser = argparse.ArgumentParser()
                        parser.add_argument('-x', type=int)
                        return parser

                app = App()
                byoc.load(app)

                print(f'{app.x=}')

        .. tab:: bash

            .. code-block:: console

                $ python app.py
                app.x=0
                $ MY_APP_X=1 python app.py
                app.x=1
                $ python app.py -x 2
                app.x=2
    """
    
    def __init__(
            self,
            *getters,
            apply: Callable | Iterable[Callable] = identity,
            pick: Callable[[ValuesIter], Any] = first,
            on_load: Optional[Callable] = None,
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
    """
    Return 
    """
    value = app[key]

    if isinstance(value, param):
        return param.get_value(app)
    else:
        return value

