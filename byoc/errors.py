class UsageError(Exception):
    pass

class CircularDependency(UsageError):
    pass


class NotYetAvailable(AttributeError):

    def __init__(self, param):
        self.param = param

class NoValueFound(AttributeError):
    pass
