from .param import param
from ..getters import Getter

class config_attr(param):

    def __init__(self, config_cls, name=None):
        self.getter = ConfigAttr(config_cls, name)
        super().__init__(self.getter)

    def __set_name__(self, owner, name):
        super().__set_name__(owner, name)
        self.getter.default_name = name

class ConfigAttr(Getter):

    def __init__(self, config_cls, name=None):
        self.config_cls = config_cls
        self.name = name
        self.default_name = None

    def iter_values(self, app, configs):
        name = self.name or self.default_name
        assert name is not None

        for config in configs:
            if not isinstance(config, self.config_cls):
                continue

            yield getattr(config, name)

