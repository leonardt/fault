import random
from hwtypes import BitVector, Bit


def random_bv(width):
    return BitVector[width](random.randint(0, (1 << width) - 1))


def random_bit():
    return Bit(random.randint(0, 1))
