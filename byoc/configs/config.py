class Config:

    def load(self):
        """
        Perform any necessary one-time initialization.
        """
        pass

    def iter_finders(self):
        raise NotImplementedError

