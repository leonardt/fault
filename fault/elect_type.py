from magma.port import Port, INPUT, OUTPUT, INOUT
from magma.t import Type, Kind


class ElectType(Type):
    def __init__(self, *largs, **kwargs):
        super().__init__(*largs, **kwargs)
        self.port = Port(self)

    @classmethod
    def is_oriented(cls, direction):
        return cls.direction == direction


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
        elif direction == INPUT:
            return ElectIn
        elif direction == OUTPUT:
            return ElectOut
        elif direction == INOUT:
            return ElectInOut
        return cls

    def flip(cls):
        if cls.is_oriented(INPUT):
            return ElectOut
        elif cls.is_oriented(OUTPUT):
            return ElectIn
        return cls


def MakeElect(**kwargs):
    return ElectKind('Elect', (ElectType,), kwargs)


Elect = MakeElect()
ElectIn = MakeElect(direction=INPUT)
ElectOut = MakeElect(direction=OUTPUT)
ElectInOut = MakeElect(direction=INOUT)
