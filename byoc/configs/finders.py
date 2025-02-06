from ..utils import lookup

class Finder:

    def iter_values(self, app, key):
        raise NotImplementedError()

class DictFinder(Finder):

    def __init__(self, values, *, schema=None, root_key=None):
        self.values = values
        self.schema = schema
        self.root_key = root_key

    def iter_values(self, app, key):
        values = self.values

        if self.root_key is not None:
            try:
                values = lookup(values, self.root_key)
            except KeyError:
                return

        if self.schema is not None:
            values = self.schema(values)

        try:
            yield lookup(values, key)
        except KeyError:
            return
