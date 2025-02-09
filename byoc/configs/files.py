from .config import Config
from .finders import DictFinder
from .utils import maybe_call
from dataclasses import dataclass
from pathlib import Path
from more_itertools import always_iterable

class FileConfig(Config):
    
    def __init__(
            self,
            path,
            *,
            schema=None,
            root_key=None,
    ):
        self.path = path
        self.schema = schema
        self.root_key = root_key

    def load(self):
        self.path = maybe_call(self.path)
        self.finders = []

        for path in always_iterable(self.path):
            try:
                values = self._parse_file(path)
            except FileNotFoundError:
                continue

            finder = DictFinder(
                    values,
                    meta=FileMeta(path),
                    schema=self.schema,
                    root_key=self.root_key,
            )
            self.finders.append(finder)

    def iter_finders(self):
        yield from self.finders

@dataclass
class FileMeta:
    path: Path

class JsonConfig(FileConfig):

    @staticmethod
    def _parse_file(path):
        import json
        with open(path) as f:
            return json.load(f)

class NtConfig(FileConfig):

    @staticmethod
    def _parse_file(path):
        import nestedtext as nt
        return nt.load(path)

class TomlConfig(FileConfig):

    @staticmethod
    def _parse_file(path):
        import tomllib
        with open(path, 'rb') as f:
            return tomllib.load(f)

class YamlConfig(FileConfig):

    @staticmethod
    def _parse_file(path):
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)

