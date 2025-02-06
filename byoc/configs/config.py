class Config:

    # Implement the loader so that the configs don't need to keep track of 
    # whether they've been loaded themselves, i.e.  keep a separate list of 
    # "loaded configs".
    def load(self):
        pass

    def iter_finders(self):
        raise NotImplementedError

def configs(method):
    method._byoc_is_config_factory = True
    return method
