import sys
import re

from .config import Config
from .finders import DictFinder
from .utils import maybe_call
from contextlib import redirect_stdout
from more_itertools import first
from textwrap import dedent
from pipeline_func import f, X

class CliConfig(Config):
    pass

class ArgparseConfig(CliConfig):
    parser_getter = lambda obj: obj.get_argparse()
    schema = None

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

        self.finder = DictFinder(
                values=vars(args),
                schema=self.schema,
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

        # If not specified:
        # - options with arguments will be None.
        # - options without arguments (i.e. flags) will be False.
        # - variable-number positional arguments (i.e. [<x>...]) will be []
        not_specified = None, False, []
        args = {k: v for k, v in args.items() if v not in not_specified}

        self.finder = DictFinder(args, schema=self.schema)

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
