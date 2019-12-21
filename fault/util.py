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


def is_valid_file_mode(file_mode):
    '''Return True if the given "file_mode" represents a valid file I/O mode'''
    return file_mode in {'r', 'w', 'rb', 'wb', 'a', 'ab', 'r+', 'rb+', 'w+',
                         'wb+', 'a+', 'ab+'}


def file_mode_allows_reading(file_mode):
    '''Return True if the given "file_mode" allows reading'''
    return file_mode in {'r', 'rb', 'r+', 'rb+', 'w+', 'wb+', 'a+', 'ab+'}


def file_mode_allows_writing(file_mode):
    '''Return True if the given "file_mode" allows writing'''
    return file_mode in {'w', 'wb', 'a', 'ab', 'r+', 'rb+', 'w+', 'wb+', 'a+',
                         'ab+'}
