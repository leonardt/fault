from magma.wire import Wire
from magma.t import Type, Kind, Direction


class ElectType(Type):
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


class ElectKind(Kind):
    __hash__ = Kind.__hash__

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        if not hasattr(cls, 'direction'):
            cls.direction = None

    def __eq__(cls, rhs):
        if not isinstance(rhs, ElectKind):
            return False

        return cls.direction == rhs.direction

    def __str__(cls):
        if cls.is_input():
            return 'In(Elect)'
        elif cls.is_output():
            return 'Out(Elect)'
        elif cls.is_inout():
            return 'InOut(Elect)'
        else:
            return 'Elect'

    def qualify(cls, direction):
        if direction is None:
            return Elect
        elif direction == Direction.In:
            return ElectIn
        elif direction == Direction.Out:
            return ElectOut
        elif direction == Direction.InOut:
            return ElectInOut
        return cls

    def flip(cls):
        if cls.is_oriented(Direction.In):
            return ElectOut
        elif cls.is_oriented(Direction.Out):
            return ElectIn
        return cls


def MakeElect(**kwargs):
    return ElectKind('Elect', (ElectType,), kwargs)


Elect = MakeElect()
ElectIn = MakeElect(direction=Direction.In)
ElectOut = MakeElect(direction=Direction.Out)
ElectInOut = MakeElect(direction=Direction.InOut)
