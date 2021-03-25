import magma as m

from fault.sva import SVAProperty
from fault.expression import Expression, UnaryOp, BinaryOp
from fault.infix import Infix
from fault.assert_utils import add_compile_guards


class Property:
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __or__(self, other):
        if isinstance(self.rhs, Infix):
            result = self.rhs.__ror__(self) | other
            self.rhs = None
            return result
        self.rhs = self.rhs | other
        return self


class Implies(Property):
    op_str = "|->"


@Infix
def implies(antecedent, consequent):
    return Implies(antecedent, consequent)


class Eventually(Property):
    op_str = "s_eventually"


@Infix
def eventually(lhs, rhs):
    return Eventually(lhs, rhs)


class Throughout(Property):
    op_str = "throughout"


@Infix
def throughout(lhs, rhs):
    return Throughout(lhs, rhs)


class Until(Property):
    op_str = "until"


@Infix
def until(lhs, rhs):
    return Until(lhs, rhs)


class UntilWith(Property):
    op_str = "until_with"


@Infix
def until_with(lhs, rhs):
    return UntilWith(lhs, rhs)


class Inside(Property):
    op_str = "inside"


@Infix
def inside(lhs, rhs):
    return Inside(lhs, rhs)


class GetItemProperty(Property):
    def __init__(self, num_cycles):
        if isinstance(num_cycles, slice):
            if num_cycles.start is None:
                raise ValueError(f"{type(self)} slice needs a start value")
            if num_cycles.step is not None:
                raise ValueError(f"{type(self)} slice cannot have a step")
        self.num_cycles = num_cycles
        self.lhs = None
        self.rhs = None

    def __or__(self, other):
        # TODO: Generalize precedence logic
        if isinstance(other, Infix):
            return other.__ror__(self)
        elif self.rhs is not None:
            self.rhs = self.rhs | other
        else:
            self.rhs = other
        return self

    def __ror__(self, other):
        self.lhs = other
        return self


class Delay(GetItemProperty):
    pass


class Repeat(GetItemProperty):
    pass


class Goto(GetItemProperty):
    pass


def make_GetItemOp(cls):
    class GetItemOp:
        def __getitem__(self, val):
            return cls(val)
    return GetItemOp


delay = make_GetItemOp(Delay)()
repeat = make_GetItemOp(Repeat)()
goto = make_GetItemOp(Goto)()


class Posedge:
    def __init__(self, value):
        self.value = value

    def compile(self, format_args):
        key = f"x{len(format_args)}"
        format_args[key] = self.value
        return f"@(posedge {{{key}}})"


def posedge(value):
    return Posedge(value)


class _Compiler:
    def __init__(self, format_args):
        self.format_args = format_args

    def _codegen_slice(self, value):
        start = value.start
        stop = value.stop
        if stop is None:
            if start not in {0, 1}:
                raise ValueError("Variable length delay only supports "
                                 "zero or more ([0:]) or one or more "
                                 "([1:]) cycles")
            return {0: "[*]", 1: "[+]"}[start]
        return f"[{start}:{stop}]"

    def _compile(self, value):
        if isinstance(value, PropertyUnaryOp):
            return f"{value.op_str} {self._compile(value.arg)}"
        # TODO: Refactor getitem properties to share code
        if isinstance(value, Delay):
            result = ""
            if value.lhs is not None:
                result += self._compile(value.lhs) + " "
            num_cycles = value.num_cycles
            if isinstance(num_cycles, slice):
                num_cycles = self._codegen_slice(num_cycles)
            return result + f"##{num_cycles} {self._compile(value.rhs)}"
        if isinstance(value, Repeat):
            result = ""
            if value.lhs is not None:
                result += self._compile(value.lhs) + " "
            num_cycles = value.num_cycles
            if isinstance(num_cycles, slice):
                num_cycles = self._codegen_slice(num_cycles)
            else:
                num_cycles = f"[*{num_cycles}]"
            return result + f"{num_cycles} {self._compile(value.rhs)}"
        if isinstance(value, Goto):
            result = ""
            if value.lhs is not None:
                result += self._compile(value.lhs) + " "
            num_cycles = value.num_cycles
            if isinstance(num_cycles, slice):
                if (num_cycles.start is None or num_cycles.stop is None or
                        num_cycles.step is not None):
                    raise ValueError(f"Invalid slice for goto: {num_cycles}")
                num_cycles = f"{num_cycles.start}:{num_cycles.stop}"
            return result + f"[-> {num_cycles}] {self._compile(value.rhs)}"
        if isinstance(value, Property):
            rhs_str = ""
            if value.rhs is not None:
                rhs_str = self._compile(value.rhs)
            return (f"{self._compile(value.lhs)} {value.op_str} "
                    f"{rhs_str}")
        if isinstance(value, m.Type):
            key = f"x{len(self.format_args)}"
            self.format_args[key] = value
            return f"{{{key}}}"
        if isinstance(value, SVAProperty):
            property_str = ""
            for arg in value.args:
                if isinstance(arg, str):
                    property_str += f" {arg} "
                elif isinstance(arg, (SVAProperty, Sequence, FunctionCall,
                                      PropertyUnaryOp, Expression)):
                    property_str += f" {self._compile(arg)} "
                else:
                    key = f"x{len(self.format_args)}"
                    self.format_args[key] = arg
                    property_str += f" {{{key}}} "
            return property_str
        if isinstance(value, Sequence):
            return f"({self._compile(value.prop)})"
        if value is None:
            return ""
        if isinstance(value, FunctionCall):
            args = ", ".join(self._compile(arg) for arg in value.args)
            return f"{value.func.name}({args})"
        if isinstance(value, set):
            contents = ", ".join(self._compile(arg) for arg in value)
            # Double escape on curly braces since this will run through format
            # inside inline_verilog logic
            return f"{{{{{contents}}}}}"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, BinaryOp):
            left = self._compile(value.left)
            right = self._compile(value.right)
            op = value.op_str
            if op == "==":
                # Use strict eq
                op = "==="
            elif op == "!=":
                # Use strict neq
                op = "!=="
            return f"({left}) {op} ({right})"
        if isinstance(value, UnaryOp):
            operand = self._compile(value.operand)
            op = value.op_str
            return f"{op} ({operand})"
        raise NotImplementedError(type(value))

    def compile(self, prop):
        compiled = self._compile(prop)
        return compiled


def _make_statement(statement, prop, on, disable_iff, compile_guard, name,
                    inline_wire_prefix):
    format_args = {}
    _compiler = _Compiler(format_args)
    prop = _compiler.compile(prop)
    disable_str = ""
    if disable_iff is not None:
        disable_str = f" disable iff ({_compiler.compile(disable_iff)})"
    event_str = on.compile(format_args)
    prop_str = f"{statement} property ({event_str}{disable_str} {prop});"
    if name is not None:
        if not isinstance(name, str):
            raise TypeError("Expected string for name")
        prop_str = f"{name}: {prop_str}"
    prop_str = add_compile_guards(compile_guard, prop_str)
    m.inline_verilog(prop_str, inline_wire_prefix=inline_wire_prefix,
                     **format_args)


def assert_(prop, on, disable_iff=None, compile_guard=None, name=None,
            inline_wire_prefix="_FAULT_ASSERT_WIRE_"):
    _make_statement("assert", prop, on, disable_iff, compile_guard, name,
                    inline_wire_prefix)


def cover(prop, on, disable_iff=None, compile_guard=None, name=None,
          inline_wire_prefix="_FAULT_COVER_WIRE_"):
    _make_statement("cover", prop, on, disable_iff, compile_guard, name,
                    inline_wire_prefix)


def assume(prop, on, disable_iff=None, compile_guard=None, name=None,
           inline_wire_prefix="_FAULT_ASSUME_WIRE_"):
    _make_statement("assume", prop, on, disable_iff, compile_guard, name,
                    inline_wire_prefix)


class Sequence:
    def __init__(self, prop):
        if not isinstance(prop, (Property, SVAProperty)):
            raise TypeError("Expected type Property or SVAProperty not "
                            f"{type(prop)}")
        self.prop = prop


def sequence(prop):
    return Sequence(prop)


class FunctionCall(Expression):
    def __init__(self, func, args):
        self.func = func
        self.args = args


class Function:
    def __init__(self, name):
        self.name = name

    def __call__(self, *args):
        return FunctionCall(self, args)


onehot0 = Function("$onehot0")
onehot = Function("$onehot")
countones = Function("$countones")
isunknown = Function("$isunknown")
past = Function("$past")
rose = Function("$rose")
fell = Function("$fell")
stable = Function("$stable")


class PropertyUnaryOp(Expression):
    pass


class Not(PropertyUnaryOp):
    op_str = "!"

    def __init__(self, arg):
        self.arg = arg


def not_(arg):
    return Not(arg)
