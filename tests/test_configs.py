import byoc
import pytest
import parametrize_from_file as pff
import shlex
import re
import sys

from byoc import Key
from glom import glom
from pathlib import Path
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

def preprocess_cli_config_params(params_in):
    params_out = []

    for param in params_in:
        for i, invocation in enumerate(param.pop('invocations')):
            params_out.append({**param, **invocation, 'id': f"{param['id']}-{i+1}"})

    return params_out


def test_env_var_config(monkeypatch):
    from byoc import EnvVarConfig

    monkeypatch.setenv('MY_APP_X', '1')

    class MyApp(MetaMixin):

        @byoc.configs
        def iter_configs(self):
            yield EnvVarConfig()

        x = byoc.param(
                Key(EnvVarConfig, 'MY_APP_X', apply=int),
        )

    app = MyApp()
    byoc.load(app)

    assert app.x == 1
    assert app.meta.x.name == 'MY_APP_X'
    assert app.meta.x.value == '1'

@pff.parametrize(
        preprocess=preprocess_cli_config_params,
        schema=[
            pff.defaults(usage=None, brief=None, stdout=None, stderr=None),
            pff.cast(argv=shlex.split, expected=with_py.eval),
            pff.error_or('expected', globals=with_byoc)
        ],
)
def test_cli_config(monkeypatch, capsys, app, usage, brief, argv, expected, error, stdout, stderr):
    with_byoc_cli = pff.Namespace(
            with_byoc, 
            byoc.CliConfig,
            byoc.ArgparseConfig,
            byoc.DocoptConfig,
    )
    app = with_byoc_cli.exec(app, get=get_app)

    # The format of the `argparse` usage text changed in Python 3.10.
    if usage and sys.version_info[:2] >= (3, 10):
        usage = re.sub('(?m)^optional arguments:$', 'options:', usage)

    monkeypatch.setattr(sys, 'argv', argv)

    with error:
        byoc.load(app)

    if not error:
        for param, value in expected.items():
            assert glom(app, param) == value

    if usage is not None:
        assert app.usage == usage
    if brief is not None:
        assert app.brief == brief

    cap = capsys.readouterr()

    if stdout is not None:
        assert cap.out == stdout
    if stderr is not None:
        assert cap.err == stderr

@pff.parametrize(indirect=['tmp_files'])
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

    with_cwd = pff.Namespace(Path=Path, CWD=tmp_files)
    expected = with_cwd.eval(expected)

    for param, value in expected.items():
        assert glom(app, param) == value

@pff.parametrize(
        schema=[
            pff.cast(
                f=with_py.exec(get='f'),
                raises=with_py.eval,
                x=with_py.eval,
                expected=with_py.eval,
            ),
            pff.defaults(raises=[]),
            pff.error_or('x', 'expected'),
        ],
)
@pytest.mark.parametrize(
        'factory', [
            pytest.param(
                lambda f, raises: byoc.dict_like(*raises)(f),
                id='decorator',
            ),
            pytest.param(
                lambda f, raises: byoc.dict_like(f, *raises),
                id='constructor',
            ),
        ]
)
def test_dict_like(factory, f, raises, x, expected, error):
    with error:
        g = factory(f, raises)
        assert g[x] == expected

def test_dict_like_repr():
    d = byoc.dict_like(int)
    assert repr(d) == "dict_like(<class 'int'>)"

