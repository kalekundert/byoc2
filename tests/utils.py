import byoc
import parametrize_from_file as pff

class DictConfig(byoc.Config):

    def __init__(self, payload):
        self.payload = payload

    def __repr__(self):
        return f'DictConfig({self.payload})'

    def iter_layers(self):
        yield byoc.Layer(self.payload, 'hard-coded')

with_py = pff.Namespace()
with_byoc = pff.Namespace(
        'import byoc',
        'from byoc import Key, Method, Func, Value',
        'from byoc import UsageError, NoValueFound',
        DictConfig=DictConfig,
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
