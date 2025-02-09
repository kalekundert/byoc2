import byoc
import parametrize_from_file as pff

from byoc import Key, Func, Value
from pytest import raises
from glom import glom
from utils import *

@pff.parametrize(
        schema=[
            pff.error_or('expected', globals=with_byoc),
        ],
)
def test_load(app, expected, error):
    with_test = with_byoc.exec(app)

    app = get_app(with_test)
    expected = with_test.eval(expected)

    with error:
        byoc.load(app)

        for param, value in expected.items():
            assert glom(app, param) == value

@pff.parametrize(
        schema=[
            pff.cast(expected=with_byoc.eval),
            pff.error_or('expected', globals=with_byoc),
            pff.defaults(configs=[], meta='None'),
        ],
)
def test_load_collection(app, configs, meta, expected, error):
    app = with_byoc.eval(app)
    configs = with_byoc.eval(configs)
    meta = pff.Namespace(with_byoc, app=app).eval(meta)
    outputs = dict(app=app, configs=configs, meta=meta)

    with error:
        byoc.load_collection(app, configs, meta=meta)

        for attr, value in expected.items():
            assert glom(outputs, attr) == value

def test_clean_up_temporary_attributes():
    children = []

    # This test is very similar to `test_load::temp-value-recursive`.  The 
    # difference is that we keep track of all the `MyChild` instances that get 
    # created during the load process, and make sure that only the last has any 
    # modifications.

    class MyConfig(byoc.Config):

        def __init__(self, get_x):
            self.get_x = get_x

        def load(self):
            self.finder = byoc.DictFinder({'x': self.get_x()})

        def iter_finders(self):
            yield self.finder

    class MyChild:
        x = byoc.param(
                Key(MyConfig, 'x'),
                Value(1),
        )

        def __init__(self):
            children.append(self)
          
    class MyApp:

        @byoc.configs
        def iter_configs(self):
            yield MyConfig(lambda: self.child.x + 1)

        child = byoc.param(
            Func(MyChild),
            on_load=byoc.recursive_load,
        )

    app = MyApp()
    byoc.load(app)

    assert len(children) == 2
    assert 'x' not in children[0].__dict__
    assert 'x' in children[1].__dict__
    assert children[1] is app.child
    assert app.child.x == 2

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

