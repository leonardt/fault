from magma.port import Port, INPUT, OUTPUT, INOUT
from magma.t import Type, Kind


class RealType(Type):
    def __init__(self, *largs, **kwargs):
        super().__init__(*largs, **kwargs)
        self.port = Port(self)

    @classmethod
    def isoriented(cls, direction):
        return cls.direction == direction

    __hash__ = Type.__hash__


class RealKind(Kind):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        if not hasattr(cls, 'direction'):
            cls.direction = None

    def __eq__(cls, rhs):
        if not isinstance(rhs, RealKind):
            return False

        return cls.direction == rhs.direction

    def __str__(cls):
        if cls.isinput():
            return 'In(Real)'
        elif cls.isoutput():
            return 'Out(Real)'
        elif cls.isinout():
            return 'InOut(Real)'
        else:
            return 'Real'

    def qualify(cls, direction):
        if direction is None:
            return Real
        elif direction == INPUT:
            return RealIn
        elif direction == OUTPUT:
            return RealOut
        elif direction == INOUT:
            return RealInOut
        return cls

    def flip(cls):
        if cls.isoriented(INPUT):
            return RealOut
        elif cls.isoriented(OUTPUT):
            return RealIn
        return cls

    __hash__ = Kind.__hash__


def MakeReal(**kwargs):
    return RealKind('Real', (RealType,), kwargs)


Real = MakeReal()
RealIn = MakeReal(direction=INPUT)
RealOut = MakeReal(direction=OUTPUT)
RealInOut = MakeReal(direction=INOUT)
