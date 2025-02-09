import os

from .config import Config
from .finders import DictFinder, dict_like
from dataclasses import dataclass

class EnvVarConfig(Config):

    def load(self):
        def get_meta(k):
            return EnvVarMeta(k, os.environ[k])

        self.finder = DictFinder(
                values=os.environ,
                meta=dict_like(get_meta),
                lookup_meta=True,
        )

    def iter_finders(self):
        yield self.finder


@dataclass
class EnvVarMeta:
    name: str
    value: str

