from .config import Config
from .finders import DictFinder
from .utils import maybe_call

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
        self.finder = DictFinder(
                self._parse_values(),
                schema=self.schema,
                root_key=self.root_key,
        )

    def iter_finders(self):
        yield self.finder

class JsonConfig(FileConfig):

    def _parse_values(self):
        import json
        with open(self.path) as f:
            return json.load(f)

class NtConfig(FileConfig):

    def _parse_values(self):
        import nestedtext as nt
        return nt.load(self.path)

class TomlConfig(FileConfig):

    def _parse_values(self):
        import tomllib
        with open(self.path, 'rb') as f:
            return tomllib.load(f)

class YamlConfig(FileConfig):

    def _parse_values(self):
        import yaml
        with open(self.path) as f:
            return yaml.safe_load(f)

