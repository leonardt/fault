import pytest
import logging
from magma.util import reset_global_context

collect_ignore = ["src"]  # pip folder that contains dependencies like magma


@pytest.fixture(autouse=True)
def magma_test():
    reset_global_context()
    logging.getLogger().setLevel(logging.DEBUG)
