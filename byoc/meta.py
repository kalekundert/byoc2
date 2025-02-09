from collections.abc import MutableSequence, MutableMapping

def meta_from_collection(collection):
    if isinstance(collection, MutableSequence):
        return [meta_from_collection(x) for x in collection]

    elif isinstance(collection, MutableMapping):
        return {k: meta_from_collection(v) for k, v in collection.items()}

    else:
        return None

