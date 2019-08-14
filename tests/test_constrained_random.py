import random
from fault.random import ConstrainedRandomGenerator

N = 8
WIDTH = 8


def test_constrained_random():
    random.seed(0)
    v = dict(x=WIDTH, y=WIDTH, z=WIDTH)

    def pred(x, y, z):
        return (((x + y) ^ z) >> 1) == WIDTH

    gen = ConstrainedRandomGenerator()

    models = gen(v, pred, N)
    assert len(models) >= N

    for m in models:
        assert pred(**m)
