import magma as m


def is_recursive_type(T):
    return (issubclass(T, m.Tuple) or issubclass(T, m.Array) and
            not issubclass(T.T, m.Digital))
