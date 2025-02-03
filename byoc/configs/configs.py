import os
import sys

from .layers import Layer
from contextlib import redirect_stdout

class Config:

    def iter_layers(self):
        raise NotImplementedError

    def iter_cached_layers(self):
        # Don't require subclasses to call `super().__init__()`.  Since this 
        # class is meant to be subclasses by end-users, I think this makes it 
        # more user-friendly.
        if not hasattr(self, '_cached_layers'):
            self._cached_layers = list(self.iter_layers())
        yield from self._cached_layers

class EnvironmentConfig(Config):

    def iter_layers(self):
        yield Layer(os.environ)

class DocoptConfig:

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
        self.usage = usage or getattr(app, '__doc__')
        self.usage_io = usage_io or sys.stdout
        self.version = version or getattr(app, '__version__')
        self.include_help = include_help
        self.include_version = include_version
        self.options_first = options_first
        self.schema = schema

    def iter_layers(self):
        import docopt

        with redirect_stdout(self.usage_io):
            args = docopt.docopt(
                    self.usage,
                    help=self.include_help,
                    version=self.version,
                    options_first=self.options_first,
            )

        args = docopt.docopt(self.doc)

        # If not specified:
        # - options with arguments will be None.
        # - options without arguments (i.e. flags) will be False.
        # - variable-number positional arguments (i.e. [<x>...]) will be []
        not_specified = None, False, []
        args = {k: v for k, v in args.items() if v not in not_specified}

        yield Layer(args)

class TomlConfig:

    def __init__(self, get_path):
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
