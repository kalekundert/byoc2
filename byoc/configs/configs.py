import os
import sys

from .layers import Layer
from contextlib import redirect_stdout

class Config:

    def __init__(self):
        self._cached_layers = None

    def load(self):
        self._cached_layers = list(self.iter_layers())

    @property
    def is_loaded(self):
        return self._cached_layers is not None

    def iter_layers(self):
        raise NotImplementedError

    def iter_cached_layers(self):
        yield from self._cached_layers

class EnvironmentConfig(Config):

    def iter_layers(self):
        yield Layer(os.environ)

class DocoptConfig(Config):

    def __init__(
            self,
            *,
            app=None,
            usage=None,
            usage_io=None,
            version=None,
            include_help=True,
            include_version=None,
            options_first=False,
            schema=None,
    ):
        super().__init__()

        self.app = app
        self.usage = usage
        self.usage_io = usage_io
        self.version = version
        self.include_help = include_help
        self.include_version = include_version
        self.options_first = options_first
        self.schema = schema

    def iter_layers(self):
        import docopt

        with redirect_stdout(self.usage_io or sys.stdout):
            args = docopt.docopt(
                    self.usage,
                    help=self.include_help,
                    version=self.version,
                    options_first=self.options_first,
            )

        # If not specified:
        # - options with arguments will be None.
        # - options without arguments (i.e. flags) will be False.
        # - variable-number positional arguments (i.e. [<x>...]) will be []
        not_specified = None, False, []
        args = {k: v for k, v in args.items() if v not in not_specified}

        yield Layer(args)

class TomlConfig(Config):

    def __init__(self, get_path):
        super().__init__()
        self.get_path = get_path

    def iter_layers(self):
        import tomllib

        path = self.get_path()

        with open(path, 'rb') as f:
            payload = tomllib.load(f)

        yield Layer(payload, path)

def configs(method):
    method._byoc_is_config_factory = True
    return method
