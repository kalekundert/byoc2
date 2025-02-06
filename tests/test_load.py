import byoc
import parametrize_from_file as pff

from byoc import Key, Value
from pytest import raises
from glom import glom
from utils import *

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

def test_only_load_each_config_once():
    num_calls = {'load': 0, 'iter_finders': 0}

    class MyConfig(DictConfig):

        def load(self):
            num_calls['load'] += 1
            super().load()

        def iter_finders(self):
            num_calls['iter_finders'] += 1
            yield from super().iter_finders()

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
    assert num_calls['load'] == 1
    assert num_calls['iter_finders'] > 1

def test_err_forget_to_load():

    class MyApp:
        x = byoc.param(Value(1))

    app = MyApp()

    with raises(byoc.UsageError, match='parameter has no value'):
        app.x

