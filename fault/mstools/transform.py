try:
    import numpy as np
except ModuleNotFoundError:
    print('Failed to import numpy for transform calculations.')


def rotmat(deg):
    th = np.radians(deg)
    s, c = np.sin(th), np.cos(th)
    return np.array([[+c, -s],
                     [+s, +c]],
                    dtype=float)


def trmat(kind):
    if kind == 'R0':
        return rotmat(0)
    elif kind == 'R90':
        return rotmat(90)
    elif kind == 'R180':
        return rotmat(180)
    elif kind == 'R270':
        return rotmat(270)
    elif kind == 'MX':
        return np.array([[+1,  0],
                         [ 0, -1]], dtype=float)
    elif kind == 'MY':
        return np.array([[-1,  0],
                         [ 0, +1]], dtype=float)
    else:
        raise Exception(f'Invalid transformation: {kind}.')

