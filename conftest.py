import pytest
from magma import clear_cachedFunctions
import magma.backend.coreir_ as coreir_

collect_ignore = ["src"]  # pip folder that contains dependencies like magma


@pytest.fixture(autouse=True)
def magma_test():
    clear_cachedFunctions()
    coreir_.__reset_context()
