import pytest
from magma import clear_cachedFunctions
import magma
import logging

collect_ignore = ["src"]  # pip folder that contains dependencies like magma


@pytest.fixture(autouse=True)
def magma_test():
    clear_cachedFunctions()
    magma.frontend.coreir_.ResetCoreIR()
    logging.getLogger().setLevel(logging.DEBUG)
