from math import ceil, log2


def clog2(x):
    return int(ceil(log2(x)))


def flatten(l):
    return [item for sublist in l for item in sublist]


def has_kratos_runtime():
    try:
        import kratos_runtime
        return True
    except ImportError:
        return False
