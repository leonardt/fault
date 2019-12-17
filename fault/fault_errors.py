class FaultError(Exception):
    pass


class A2DError(FaultError):
    pass


class ExpectError(FaultError):
    pass
