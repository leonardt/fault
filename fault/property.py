from functools import partial

import magma as m

from fault.sva import SVAProperty


class Property:
    pass


class Infix:
    def __init__(self, func):
        self.func = func

    def __or__(self, other):
        return self.func(other)

    def __ror__(self, other):
        return Infix(partial(self.func, other))


class Implies(Property):
    def __init__(self, antecedent, consequent):
        self.antecedent = antecedent
        self.consequent = consequent

    def __or__(self, other):
        self.consequent = self.consequent | other
        return self


@Infix
def implies(antecedent, consequent):
    return Implies(antecedent, consequent)


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
    def __init__(self):
        self.format_args = {}

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
        if isinstance(value, Implies):
            return (f"{self._compile(value.antecedent)} |-> "
                    f"{self._compile(value.consequent)}")
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
        if isinstance(value, m.Type):
            key = f"x{len(self.format_args)}"
            self.format_args[key] = value
            return f"{{{key}}}"
        if isinstance(value, SVAProperty):
            property_str = ""
            for arg in value.args:
                if isinstance(arg, str):
                    property_str += f" {arg} "
                elif isinstance(arg, (SVAProperty, Sequence)):
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
        raise NotImplementedError(type(value))

    def compile(self, prop):
        compiled = self._compile(prop)
        return compiled, self.format_args


def assert_(prop, on):
    prop, format_args = _Compiler().compile(prop)
    event_str = on.compile(format_args)
    m.inline_verilog(
        f"assert property ({event_str} {prop});", **format_args
    )


class Sequence:
    def __init__(self, prop):
        if not isinstance(prop, (Property, SVAProperty)):
            raise TypeError("Expected type Property or SVAProperty not "
                            f"{type(prop)}")
        self.prop = prop


def sequence(prop):
    return Sequence(prop)
