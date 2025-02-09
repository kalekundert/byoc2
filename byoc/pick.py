from .errors import NoValueFound
from funcy import autocurry

class ValuesIter:

    def __init__(self, param, values):
        self.param = param
        self.values = values
        self.meta = None

    def __iter__(self):
        yield from (v for v, m in self.with_meta)

    @property
    def with_meta(self):
        yield from self.values

def first(it: ValuesIter):
    try:
        value, meta = next(iter(it.with_meta))
        it.meta = meta
        return value
    except StopIteration:
        raise NoValueFound(f'no value found for {it.param!r}') from None

def list(it: ValuesIter):
    from builtins import list

    items = list(zip(*it.with_meta))

    if items:
        values, metas = map(list, items)
    else:
        values, metas = [], []

    it.meta = metas
    return values

@autocurry
def merge_dicts(it: ValuesIter, keep_last: bool = False):
    values = {}
    it.meta = {}

    for dict_, meta in it.with_meta:
        for key, value in dict_.items():
            if (key not in values) or keep_last:
                values[key] = value
                it.meta[key] = meta

    return values



