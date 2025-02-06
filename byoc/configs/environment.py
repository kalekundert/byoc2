import os

from .config import Config
from .finders import DictFinder

class EnvironmentConfig(Config):

    def iter_finders(self):
        yield DictFinder(os.environ)

