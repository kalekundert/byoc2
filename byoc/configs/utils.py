def maybe_call(x):
    return x() if callable(x) else x
