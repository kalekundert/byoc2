import byoc
import parametrize_from_file as pff

class DictConfig(byoc.Config):

    def __init__(self, values):
        self.values = values

    def __repr__(self):
        return f'DictConfig({self.payload})'

    def iter_finders(self):
        yield byoc.DictFinder(self.values)

def star_keys(d):
    return {f'{k}*': v for k, v in d.items()}

with_py = pff.Namespace()
with_byoc = pff.Namespace(
        'import byoc',
        'from byoc import Key, Method, Func, Value',
        'from byoc import UsageError, NoValueFound',
        DictConfig,
        star_keys,
)

def get_obj(obj_name, cls_name=None):
    if not cls_name:
        cls_name = f'My{obj_name.title()}'

    def get(ns):
        try:
            return ns[obj_name]
        except KeyError:
            return ns[cls_name]()

    return get

get_app = get_obj('app')
