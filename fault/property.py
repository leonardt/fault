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


class Delay(Property):
    def __init__(self, num_cycles):
        self.num_cycles = num_cycles
        self.lhs = None
        self.rhs = None

    def __or__(self, other):
        if self.rhs is not None:
            self.rhs = self.rhs | other
        else:
            self.rhs = other
        return self

    def __ror__(self, other):
        self.lhs = other
        return self


class DelayOp:
    def __getitem__(self, val):
        return Delay(val)


delay = DelayOp()


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

    def _compile(self, value):
        if isinstance(value, Implies):
            return (f"{self._compile(value.antecedent)} |-> "
                    f"{self._compile(value.consequent)}")
        if isinstance(value, Delay):
            result = ""
            if value.lhs:
                result += self._compile(value.lhs) + " "
            return result + f"##{value.num_cycles} {self._compile(value.rhs)}"
        if isinstance(value, m.Type):
            key = f"x{len(self.format_args)}"
            self.format_args[key] = value
            return f"{{{key}}}"
        if isinstance(value, SVAProperty):
            property_str = ""
            for arg in value.args:
                if isinstance(arg, str):
                    property_str += f" {arg} "
                else:
                    key = f"x{len(self.format_args)}"
                    self.format_args[key] = arg
                    property_str += f" {{{key}}} "
            return property_str
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
