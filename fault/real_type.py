from magma.wire import Wire
from magma.t import Type, Kind, Direction


class RealType(Type):
    def __init__(self, *largs, **kwargs):
        super().__init__(*largs, **kwargs)
        self._wire = Wire(self)

    @classmethod
    def is_oriented(cls, direction):
        return cls.direction == direction

    def wired(self):
        return self._wire.wired()

    def trace(self):
        return self._wire.trace()

    def value(self):
        return self._wire.value()

    def driven(self):
        return self._wire.driven()


class RealKind(Kind):
    __hash__ = Kind.__hash__

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        if not hasattr(cls, 'direction'):
            cls.direction = None

    def __eq__(cls, rhs):
        if not isinstance(rhs, RealKind):
            return False

        return cls.direction == rhs.direction

    def __str__(cls):
        if cls.is_input():
            return 'In(Real)'
        elif cls.is_output():
            return 'Out(Real)'
        elif cls.is_inout():
            return 'InOut(Real)'
        else:
            return 'Real'

    def qualify(cls, direction):
        if direction is None:
            return Real
        elif direction == Direction.In:
            return RealIn
        elif direction == Direction.Out:
            return RealOut
        elif direction == Direction.InOut:
            return RealInOut
        return cls

    def flip(cls):
        if cls.is_oriented(Direction.In):
            return RealOut
        elif cls.is_oriented(Direction.Out):
            return RealIn
        return cls


def MakeReal(**kwargs):
    return RealKind('Real', (RealType,), kwargs)


Real = MakeReal()
RealIn = MakeReal(direction=Direction.In)
RealOut = MakeReal(direction=Direction.Out)
RealInOut = MakeReal(direction=Direction.InOut)
