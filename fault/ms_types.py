from magma import Digital, Direction


class RealType(Digital):
    pass


RealIn = RealType[Direction.In]
RealOut = RealType[Direction.Out]
RealInOut = RealType[Direction.InOut]


class CurrentType(Digital):
    pass


CurrentIn = CurrentType[Direction.In]
CurrentOut = CurrentType[Direction.Out]
CurrentInOut = CurrentType[Direction.InOut]


class ElectType(Digital):
    pass


ElectIn = ElectType[Direction.In]
ElectOut = ElectType[Direction.Out]
ElectInOut = ElectType[Direction.InOut]
