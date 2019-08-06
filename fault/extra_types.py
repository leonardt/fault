import magma as m
from magma.bit import MakeBit
from magma.port import INPUT, OUTPUT

# Hacky definition of analog types.  A more fully-fledged
# version should probably be moved to magma at some point

ElectIn = MakeBit(direction=INPUT)
ElectOut = MakeBit(direction=OUTPUT)

RealIn = MakeBit(direction=INPUT)
RealOut = MakeBit(direction=OUTPUT)
