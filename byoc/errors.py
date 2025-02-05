from tidyexc import Error

class UsageError(Error):
    pass

class NoValueFound(AttributeError):
    pass
