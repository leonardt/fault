from magma.t import Type
from fault.infix import Infix
import pysv


class Expression:
    def __and__(self, other):
        return And(self, other)

    def __rand__(self, other):
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

    def __radd__(self, other):
        return Add(otehr,self)

    def __invert__(self):
        return Invert(self)

    def __lshift__(self, other):
        return LShift(self, other)

    def __rlshift__(self, other):
        return LShift(other, self)

    def __rshift__(self, other):
        return RShift(self, other)

    def __rrshift__(self, other):
        return RShift(other, self)

    def __mod__(self, other):
        return Mod(self, other)

    def __rmod__(self, other):
        return Mod(otehr, self)

    def __mul__(self, other):
        return Mul(self, other)

    def __rmul__(self, other):
        return Mul(other, self)

    def __neg__(self):
        return Neg(self)

    def __pos__(self):
        return Pos(self)

    def __pow__(self, other):
        raise NotImplementedError("Pow not supported as an operator in magma,"
                                  " C, or hwtypes")
        return Pow(self, other)

    def __sub__(self, other):
        return Sub(self, other)

    def __rsub__(self, other):
        return Sub(other, self)

    def __truediv__(self, other):
        return Div(self, other)

    def __rtruediv__(self, other):
        return Div(other, self)

    def __or__(self, other):
        if isinstance(other, Infix):
            # Force Infix operator logic
            return NotImplemented
        return Or(self, other)

    def __ror__(self, other):
        return Or(other, self)

    def __xor__(self, other):
        return XOr(self, other)

    def __rxor__(self, other):
        return XOr(other, self)


class BinaryOp(Expression):
    def __init__(self, left, right):
        self.left = left
        self.right = right


class UnaryOp(Expression):
    def __init__(self, operand):
        self.operand = operand


class And(BinaryOp):
    op_str = "&"


class EQ(BinaryOp):
    op_str = "=="


class NE(BinaryOp):
    op_str = "!="


class LT(BinaryOp):
    op_str = "<"


class LE(BinaryOp):
    op_str = "<="


class GT(BinaryOp):
    op_str = ">"


class GE(BinaryOp):
    op_str = ">="


class Add(BinaryOp):
    op_str = "+"


class Invert(UnaryOp):
    op_str = "~"


class LShift(BinaryOp):
    op_str = "<<"


class RShift(BinaryOp):
    op_str = ">>"


class Mod(BinaryOp):
    op_str = "%"


class Mul(BinaryOp):
    op_str = "*"


class Neg(UnaryOp):
    op_str = "-"


class Pos(UnaryOp):
    op_str = "+"


class Pow(BinaryOp):
    op_str = "**"


class Sub(BinaryOp):
    op_str = "-"


class Div(BinaryOp):
    op_str = "/"


class XOr(BinaryOp):
    op_str = "^"


class Or(BinaryOp):
    op_str = "|"


class FunctionCall(Expression):
    def __init__(self, *args):
        self.args = args


class Abs(FunctionCall):
    func_str = "abs"


def abs(x):
    return Abs(x)


class Min(FunctionCall):
    func_str = "min"


def min(x, y):
    return Min(x, y)


class Max(FunctionCall):
    func_str = "max"


def max(x, y):
    return Max(x, y)


class Signed(FunctionCall):
    func_str = "signed"


def signed(x):
    return Signed(x)


class Integer(FunctionCall):
    func_str = "int'"


def integer(x):
    return Integer(x)


class CallExpression(Expression):
    def __init__(self, func, *args, **kwargs):
        if type(func) == type:
            func = func.__init__
        assert isinstance(func, pysv.function.DPIFunctionCall)
        self.call_inst = pysv.make_call(func, *args, **kwargs)
        # get the class instance name
        if func.meta is not None:
            self.name = func.meta
            func.meta = None
        else:
            self.name = None

    def str(self, is_sv, arg_to_str, use_ptr=False):
        return self.call_inst.str(is_sv, arg_to_str, class_var_name=self.name, use_ptr=use_ptr)
