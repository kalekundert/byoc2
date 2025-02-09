from ..utils import lookup
from smartcall import call, PosOnly, KwOnly

class Finder:

    def iter_values(self, app, key):
        raise NotImplementedError()

class DictFinder(Finder):

    def __init__(
            self,
            values,
            meta=None,
            *,
            schema=None,
            root_key=None,
            lookup_meta=False,
    ):
        self.values = values
        self.meta = meta
        self.schema = schema
        self.root_key = root_key
        self.lookup_meta = lookup_meta

    def iter_values(self, app, key):
        values = self.values
        meta = self.meta

        if self.root_key is not None:
            try:
                values = lookup(values, self.root_key)
                if self.lookup_meta:
                    meta = lookup(meta, self.root_key)
            except KeyError:
                return

        if self.schema is not None:
            values = call(
                    self.schema,
                    PosOnly(values, required=True),
                    KwOnly(meta=meta),
            )

        try:
            value = lookup(values, key)
            if self.lookup_meta:
                meta = lookup(meta, key)
        except KeyError:
            return

        yield value, meta

def dict_like(*args):
    from inspect import isclass

    # I want this function to be usable as a decorator, but I also want to 
    # avoid exposing `__call__()` so that these objects don't look like 
    # deferred values to `Layer`.  These competing requirements necessitate an 
    # awkward layering of wrapper functions and classes.
    
    class dict_like:

        def __init__(self, f, *raises):
            self.f = f
            self.raises = raises

        def __repr__(self):
            return f"{self.__class__.__name__}({self.f!r})"

        def __getitem__(self, key):
            try:
                return self.f(key)
            except tuple(self.raises) as err:
                raise KeyError from err

    is_exception = lambda x: isclass(x) and issubclass(x, Exception)

    if not args:
        return lambda f: dict_like(f)

    elif is_exception(args[0]):
        return lambda f: dict_like(f, *args)

    else:
        return dict_like(*args)

