import byoc
import parametrize_from_file as pff

from byoc import Key
from glom import glom
from utils import *

# I want to test that priority is working correctly.  However, first I need a 
# way to record a log of the loading process.

@pff.parametrize(
        schema=[
            pff.cast(expected=with_py.eval),
            pff.error_or('expected', globals=with_byoc),
        ],
)
def test_load(app, expected, error):
    with error:
        app = with_byoc.exec(app, get=get_app)
        byoc.load(app)

        for param, value in expected.items():
            assert glom(app, param) == value

@pff.parametrize(
        schema=[
            pff.defaults(configs=[]),
            pff.cast(expected=with_py.eval),
            pff.error_or('expected', globals=with_byoc),
        ],
)
def test_load_collection(app, configs, expected, error):
    with error:
        app = with_byoc.eval(app)
        configs = with_byoc.eval(configs)

        byoc.load_collection(app, configs)

        for param, value in expected.items():
            assert glom(app, param) == value

def test_load_config_cache():
    num_iter_layers_calls = 0

    class MyConfig(DictConfig):

        def iter_layers(self):
            nonlocal num_iter_layers_calls
            num_iter_layers_calls += 1
            yield from super().iter_layers()

    class MyApp:

        @byoc.configs
        def iter_configs(self):
            yield MyConfig({'x': 1, 'y': 2})

        x = byoc.param(Key(MyConfig, 'x'))
        y = byoc.param(Key(MyConfig, 'y'))

    app = MyApp()
    byoc.load(app)

    assert app.x == 1
    assert app.y == 2
    assert num_iter_layers_calls == 1
