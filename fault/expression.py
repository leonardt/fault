class Expression:
    pass


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
