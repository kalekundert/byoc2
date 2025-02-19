#!/usr/bin/env python3

import byoc
from byoc import Config, Key, Value, DictFinder

# These tests aren't meant to catch errors.  Instead, they're to help with 
# debugging when I've done something that totally breaks the library and need 
# some simple test cases to help me figure out what's going on.

class DictConfig(Config):

    def __init__(self, values):
        self.values = values

    def iter_finders(self):
        yield DictFinder(values=self.values)

def test_easy_1():

    class MyApp:
        x = byoc.param(Value(1))

    app = MyApp()
    byoc.load(app)

    assert app.x == 1

def test_easy_2():

    class MyApp:

        @byoc.configs
        def iter_configs(self):
            yield DictConfig({'x': 1})

        x = byoc.param(Key(DictConfig, 'x'))

    app = MyApp()
    byoc.load(app)

    assert app.x == 1

def test_easy_3():

    class MyApp:

        @byoc.configs
        def iter_configs(self):
            yield DictConfig({'x': 1, 'y': 1})
            yield DictConfig({'x': 2, 'z': 2})

        x = byoc.param(Key(DictConfig, 'x'))
        y = byoc.param(Key(DictConfig, 'y'))
        z = byoc.param(Key(DictConfig, 'z'))

    app = MyApp()
    byoc.load(app)

    assert app.x == 1
    assert app.y == 1
    assert app.z == 2
