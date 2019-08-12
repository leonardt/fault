from magma.port import Port, INPUT, OUTPUT, INOUT
from magma.t import Type, Kind


class ElectType(Type):
    def __init__(self, *largs, **kwargs):
        super().__init__(*largs, **kwargs)
        self.port = Port(self)

    @classmethod
    def isoriented(cls, direction):
        return cls.direction == direction


class ElectKind(Kind):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        if not hasattr(cls, 'direction'):
            cls.direction = None

    def __eq__(cls, rhs):
        if not isinstance(rhs, ElectKind):
            return False

        return cls.direction == rhs.direction

    def __str__(cls):
        if cls.isinput():
            return 'In(Elect)'
        elif cls.isoutput():
            return 'Out(Elect)'
        elif cls.isinout():
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
        if cls.isoriented(INPUT):
            return ElectOut
        elif cls.isoriented(OUTPUT):
            return ElectIn
        return cls


def MakeElect(**kwargs):
    return ElectKind('Elect', (ElectType,), kwargs)


Elect = MakeElect()
ElectIn = MakeElect(direction=INPUT)
ElectOut = MakeElect(direction=OUTPUT)
ElectInOut = MakeElect(direction=INOUT)
