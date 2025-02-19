import sys
import re

from .config import Config
from .finders import DictFinder
from .utils import maybe_call
from dataclasses import dataclass
from contextlib import redirect_stdout
from more_itertools import first
from textwrap import dedent
from pipeline_func import f, X

class CliConfig(Config):
    pass

@dataclass
class CliMeta:
    name: str
    value: str

class ArgparseConfig(CliConfig):
    """
    Parse command-line arguments using the built-in `argparse` module.

    If you are interested in the metadata provided by this config, e.g. the 
    names of the arguments corresponding to each value, be aware that they are 
    not very accurate.  The `argparse` module unfortunately provides little 
    information about how the parsed arguments relate to the original 
    command-line, so we have to do the best with what we have.
    """

    def __init__(
            self,
            parser,
            *,
            schema=None,
    ):
        self.parser = parser
        self.schema = schema

    def load(self):
        self.parser = maybe_call(self.parser)
        args = self.parser.parse_args()

        # If not specified:
        # - optional positional arguments (i.e. `nargs='?'`) will be None
        # - variable-number positional arguments (i.e. `nargs='*'`) will be []
        # - options without arguments (i.e. flags) will be False.
        not_specified = None, False, []

        values = {
                k: v
                for k, v in vars(args).items()
                if v not in not_specified
        }
        meta = {
                k: CliMeta(k, v)
                for k, v in values.items()
        }

        self.finder = DictFinder(
                values, meta,
                schema=self.schema,
                lookup_meta=True,
        )

    def iter_finders(self):
        yield self.finder

    @property
    def usage(self):
        return self.parser.format_help()

    @property
    def brief(self):
        return self.parser.description

class DocoptConfig(CliConfig):
    """
    Parse command-line arguments using the docopt_ library.
    """

    def __init__(
            self,
            usage,
            *,
            usage_io=None,
            version=None,
            include_help=True,
            options_first=False,
            schema=None,
    ):
        self.usage = usage
        self.usage_io = usage_io
        self.version = version
        self.include_help = include_help
        self.options_first = options_first
        self.schema = schema

    def load(self):
        import docopt
        
        self.usage = (
                self.usage
                | f(maybe_call)
                | f(dedent)
                # Trailing whitespace can cause unnecessary line wrapping.
                | f(re.sub, r' *$', '', X, flags=re.MULTILINE)
        )
        self.usage_io = maybe_call(self.usage_io) or sys.stdout
        self.version = maybe_call(self.version)

        with redirect_stdout(self.usage_io):
            args = docopt.docopt(
                    self.usage,
                    help=self.include_help,
                    version=self.version,
                    options_first=self.options_first,
            )

        meta = {
                k: CliMeta(k, v)
                for k, v in args.items()
        }

        # If not specified:
        # - options with arguments will be None.
        # - options without arguments (i.e. flags) will be False.
        # - variable-number positional arguments (i.e. [<x>...]) will be []
        not_specified = None, False, []
        args = {k: v for k, v in args.items() if v not in not_specified}

        self.finder = DictFinder(
                args, meta,
                schema=self.schema,
                lookup_meta=True,
        )

    def iter_finders(self):
        yield self.finder

    @property
    def brief(self):
        import re
        sections = re.split(
                '\n\n|usage:',
                self.usage,
                flags=re.IGNORECASE,
        )
        return first(sections, '').replace('\n', ' ').strip()

def mako_usage(app, template=None, extra_vars=None):
    """
    Generate usage text formatting the app's docstring as a Mako template, with 
    the app itself as a template argument.

    This allows incorporating attributes of the app (e.g. default values of 
    various parameters) into the usage text.

    If you'd like to use a template engine other than Mako, you'll need to 
    write your own version of this function.  It's not a very complicated 
    function, though.
    """

    def get_usage():
        from mako.template import Template

        usage = maybe_call(template) or app.__doc__
        usage = dedent(usage)
        usage = Template(usage, strict_undefined=True).render(
                app=app,
                **(extra_vars or {}),
        )

        return usage

    return get_usage
