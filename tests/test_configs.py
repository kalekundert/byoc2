import byoc
import pytest
import parametrize_from_file as pff
import shlex
import re
import sys

from byoc import Key
from voluptuous import Schema
from glom import glom
from utils import *

@pytest.fixture
def tmp_chdir(tmp_path):
    import os
    try:
        cwd = os.getcwd()
        os.chdir(tmp_path)
        yield tmp_path
    finally:
        os.chdir(cwd)


def test_environment_config(monkeypatch):
    from byoc import EnvironmentConfig

    monkeypatch.setenv('X', '1')

    class MyApp:

        @byoc.configs
        def iter_configs(self):
            yield EnvironmentConfig()

        x = byoc.param(
                Key(EnvironmentConfig, 'X'),
        )

    app = MyApp()
    byoc.load(app)

    assert app.x == '1'

@pff.parametrize(
        schema=pff.cast(
            invocations=Schema([{
                'argv': shlex.split,
                'expected': {str: with_py.eval},
            }]),
        ),
)
def test_cli_config(monkeypatch, app, usage, brief, invocations):
    from copy import copy

    with_byoc_cli = pff.Namespace(
            with_byoc, 
            byoc.CliConfig,
            byoc.ArgparseConfig,
            byoc.DocoptConfig,
    )
    app = with_byoc_cli.exec(app, get=get_app)

    # The format of the `argparse` usage text changed in Python 3.10.
    if sys.version_info[:2] >= (3, 10):
        usage = re.sub('(?m)^optional arguments:$', 'options:', usage)

    for invocation in invocations:
        print(invocation)

        test_app = copy(app)
        test_argv = invocation['argv']
        test_expected = invocation['expected']

        monkeypatch.setattr(sys, 'argv', test_argv)
        byoc.load(test_app)

        assert test_app.usage == usage
        assert test_app.brief == brief

        for param, value in test_expected.items():
            assert glom(test_app, param) == value

@pff.parametrize(
        schema=pff.cast(expected=with_py.eval),
        indirect=['tmp_files'],
)
def test_file_config(tmp_chdir, tmp_files, app, expected):
    with_byoc_file = pff.Namespace(
            with_byoc,
            byoc.FileConfig,
            byoc.YamlConfig,
            byoc.TomlConfig,
            byoc.NtConfig,
            byoc.JsonConfig,
    )
    app = with_byoc_file.exec(app, get=get_app)
    byoc.load(app)

    for param, value in expected.items():
        assert glom(app, param) == value
