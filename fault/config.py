__TEST_DIR = 'normal'


def set_test_dir(target):
    """
    Set to 'callee_file_dir' to have the `directory` parameter to
    `compile_and_run` relative to the calling file (default is relative to
    where Python is invoked)
    """
    global __TEST_DIR
    assert target in ['normal', 'callee_file_dir']
    __TEST_DIR = target


def get_test_dir():
    return __TEST_DIR
