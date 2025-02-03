from .errors import NoValueFound

class ValuesIter:

    def __init__(self, param, values):
        self.param = param
        self.values = values

    def __iter__(self):
        yield from self.values

def first(values: ValuesIter):
    try:
        return next(iter(values))
    except StopIteration:
        raise NoValueFound(f'no value found for {values.param!r}') from None
