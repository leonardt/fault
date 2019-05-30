class Expression:
    def __and__(self, other):
        return And(self, other)

    def __eq__(self, other):
        return EQ(self, other)

    def __ne__(self, other):
        return NE(self, other)

    def __lt__(self, other):
        return LT(self, other)

    def __le__(self, other):
        return LE(self, other)

    def __gt__(self, other):
        return GT(self, other)

    def __ge__(self, other):
        return GE(self, other)

    def __add__(self, other):
        return Add(self, other)

    def __invert__(self):
        return Invert(self)

    def __lshift__(self, other):
        return LShift(self, other)

    def __rshift__(self, other):
        return RShift(self, other)

    def __mod__(self, other):
        return Mod(self, other)

    def __mul__(self, other):
        return Mul(self, other)

    def __neg__(self):
        return Neg(self)

    def __pos__(self):
        return Pos(self)

    def __pow__(self, other):
        return Pow(self, other)

    def __sub__(self, other):
        return Sub(self, other)

    def __truediv__(self, other):
        return Div(self, other)

    def __or__(self, other):
        return Or(self, other)

    def __xor__(self, other):
        return XOr(self, other)


class BinaryOp(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class UnaryOp(Expression):
    def __init__(self, operand):
        self.operand = operand


class And(BinaryOp):
    pass


class EQ(BinaryOp):
    pass


class NE(BinaryOp):
    pass


class LT(BinaryOp):
    pass


class LE(BinaryOp):
    pass


class GT(BinaryOp):
    pass


class GE(BinaryOp):
    pass


class Add(BinaryOp):
    pass


class Invert(UnaryOp):
    pass


class LShift(BinaryOp):
    pass


class RShift(BinaryOp):
    pass


class Mod(BinaryOp):
    pass


class Mul(BinaryOp):
    pass


class Neg(UnaryOp):
    pass


class Pos(UnaryOp):
    pass


class Pow(BinaryOp):
    pass


class Sub(BinaryOp):
    pass


class Div(BinaryOp):
    pass


class XOr(BinaryOp):
    pass


class Or(BinaryOp):
    pass
