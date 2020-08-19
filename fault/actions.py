from abc import ABC, abstractmethod

from .ms_types import (RealIn, RealOut, RealInOut,
                       ElectIn, ElectOut, ElectInOut)

import fault
from fault.select_path import SelectPath
import fault.expression as expression


class Action(ABC):
    @abstractmethod
    def retarget(self, new_circuit, clock):
        """
        Create a copy of the action for `new_circuit` with `clock`
        """
        raise NotImplementedError()

    def __repr__(self):
        return str(self)


class PortAction(Action):
    def __init__(self, port, value):
        super().__init__()
        self.port = port
        self.value = value

    def __str__(self):
        type_name = type(self).__name__
        return f"{type_name}({self.port.debug_name}, {self.value})"

    def retarget(self, new_circuit, clock):
        cls = type(self)
        port = self.port
        if isinstance(port, SelectPath):
            port = port[-1]

        new_port = new_circuit.interface.ports[str(port.name)]
        return cls(new_port, self.value)


def is_input(port):
    if isinstance(port, SelectPath):
        port = port[-1]
    if isinstance(port, fault.WrappedVerilogInternalPort):
        return port.type_.is_input()
    else:
        return port.is_input()


class Poke(PortAction):
    def __init__(self, port, value, delay=None):
        if is_input(port):
            raise ValueError(f"Can only poke inputs: {port.debug_name} "
                             f"{type(port)}")
        self.delay = delay
        super().__init__(port, value)


class Print(Action):
    def __init__(self, format_str, *args):
        super().__init__()
        format_str = format_str.replace("\n", "\\n")
        self.format_str = format_str
        self.ports = args

    def __str__(self):
        ports_str = ", ".join(port.debug_name for port in self.ports)
        return f"Print(\"{self.format_str}\", {ports_str})"

    def retarget(self, new_circuit, clock):
        cls = type(self)
        new_ports = (new_circuit.interface.ports[str(port.name)] for port in
                     self.ports)
        return cls(self.format_str, *new_ports)


def is_inout(port):
    if isinstance(port, SelectPath):
        port = port[-1]
    if isinstance(port, fault.WrappedVerilogInternalPort):
        return port.type_.is_inout()
    else:
        return port.is_inout()


def is_output(port):
    if isinstance(port, SelectPath):
        port = port[-1]
    if isinstance(port, fault.WrappedVerilogInternalPort):
        return not port.type_.is_output()
    else:
        return not port.is_output()


class GetValue(Action):
    def __init__(self, port):
        super().__init__()
        self.port = port
        self.value = None  # value to be assigned after simulation

    @property
    def real_number_port(self):
        return isinstance(self.port, (RealIn, RealOut, RealInOut,
                                      ElectIn, ElectOut, ElectInOut))

    def get_format(self):
        return '%0f' if self.real_number_port else '%0d'

    def update_from_line(self, line):
        if self.real_number_port:
            self.value = float(line.strip())
        else:
            self.value = int(line.strip())

    def __str__(self):
        return f'GetValue("{self.port}")'

    def retarget(self, new_circuit, clock):
        cls = type(self)
        new_port = new_circuit.interface.ports[str(self.port.name)]
        return cls(new_port)


class Expect(PortAction):
    def __init__(self, port, value, strict=False, abs_tol=None, rel_tol=None,
                 above=None, below=None, caller=None, msg=None):
        # call super constructor
        super().__init__(port, value)

        # compute bounds if applicable
        if abs_tol is not None or rel_tol is not None:
            # sanity check
            if above is not None or below is not None:
                raise Exception('Cannot provide both abs_tol/rel_tol and above/below.')  # noqa

            # default settings
            rel_tol = rel_tol if rel_tol is not None else 0
            abs_tol = abs_tol if abs_tol is not None else 0

            # sanity check
            assert rel_tol >= 0 and abs_tol >= 0, 'rel_tol and abs_tol must be non-negative.'  # noqa

            above = value - rel_tol * abs(value) - abs_tol
            below = value + rel_tol * abs(value) + abs_tol

        # save settings
        self.strict = strict
        self.above = above
        self.below = below
        self.caller = caller
        if msg is not None and not isinstance(msg, (str, tuple)):
            raise ValueError("Expected string or tuple of form (format_str,"
                             " format_args...) for expect msg")
        self.msg = msg

    @property
    def traceback(self):
        if self.caller is not None:
            return f'{self.caller.filename}:{self.caller.lineno}'
        else:
            return None


class Assume(PortAction):
    def __init__(self, port, value):
        if is_input(port):
            raise ValueError(f"Can only assume inputs (got {port.debug_name}"
                             f" of type {type(port)})")
        super().__init__(port, value)


class Guarantee(PortAction):
    def __init__(self, port, value):
        if not is_output(port):
            raise ValueError(f"Can only guarantee on outputs (got"
                             f"{port.debug_name} of type {type(port)})")
        super().__init__(port, value)


class Peek(Action, expression.Expression):
    def __init__(self, port):
        super().__init__()
        self.port = port

    def retarget(self, new_circuit, clock):
        cls = type(self)
        new_port = new_circuit.interface.ports[str(self.port.name)]
        return cls(new_port)

    def __str__(self):
        return f"Peek({self.port.debug_name})"


class Eval(Action):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "Eval()"

    def retarget(self, new_circuit, clock):
        return Eval()


class Delay(Action):
    def __init__(self, time):
        super().__init__()
        self.time = time

    def __str__(self):
        return f'Delay({self.time})'

    def retarget(self, new_circuit, clock):
        return Delay(time=self.time)


class Step(Action):
    def __init__(self, clock, steps):
        super().__init__()
        # TODO(rsetaluri): Check if `clock` is a clock type?
        self.clock = clock
        self.steps = steps

    def __str__(self):
        return f"Step({self.clock.debug_name}, steps={self.steps})"

    def retarget(self, new_circuit, clock):
        return Step(clock, self.steps)


class Loop(Action):
    def __init__(self, n_iter, loop_var, actions, count='up'):
        self.n_iter = n_iter
        self.actions = actions
        self.loop_var = loop_var
        self.count = count

    def __str__(self):
        # TODO: Might be nice to format this print output over multiple lines
        # for actions
        return f"Loop({self.n_iter}, {self.loop_var}, {self.actions}, {self.count})"  # noqa

    def retarget(self, new_circuit, clock):
        actions = [action.retarget(new_circuit, clock) for action in
                   self.actions]
        return Loop(n_iter=self.n_iter, loop_var=self.loop_var,
                    actions=actions, count=self.count)


class FileOpen(Action):
    def __init__(self, file):
        """
        mode: "r" or "w" for read/write permissions
        """
        super().__init__()
        self.file = file

    def __str__(self):
        return f"FileOpen({self.file})"

    def retarget(self, new_circuit, clock):
        return FileOpen(self.file)


class FileRead(Action):
    def __init__(self, file):
        super().__init__()
        self.file = file

    def __str__(self):
        return f"FileRead({self.file})"

    def retarget(self, new_circuit, clock):
        return FileRead(self.file)


class FileWrite(Action):
    def __init__(self, file, value):
        super().__init__()
        self.file = file
        self.value = value

    def __str__(self):
        return f"FileWrite({self.file}, {self.value})"

    def retarget(self, new_circuit, clock):
        return FileWrite(self.file, self.value)


class FileClose(Action):
    def __init__(self, file):
        super().__init__()
        self.file = file

    def __str__(self):
        return f"FileClose({self.file})"

    def retarget(self, new_circuit, clock):
        return FileClose(self.file)


class While(Action):
    def __init__(self, loop_cond, actions):
        # TODO: might be nice to define loop_var to capture condition
        # and use in loop? e.g. if you're looping until you get a HALT
        # back from whatever you're expecting but want to switch on
        # the other opcodes?
        self.loop_cond = loop_cond
        self.actions = actions

    def __str__(self):
        return f"While({self.loop_cond}, {self.actions})"

    def retarget(self, new_circuit, clock):
        actions = [action.retarget(new_circuit, clock) for action in
                   self.actions]
        return While(self.loop_cond, actions)


class If(Action):
    def __init__(self, cond, actions, else_actions=None):
        self.cond = cond
        self.actions = actions
        self.else_actions = else_actions

    def __str__(self):
        return f"If({self.cond}, {self.actions})"

    def retarget(self, new_circuit, clock):
        actions = [action.retarget(new_circuit, clock) for action in
                   self.actions]
        return If(self.cond, actions)


class FileScanFormat(Action):
    def __init__(self, file, _format, *args):
        super().__init__()
        self.file = file
        self._format = _format
        assert len(args) >= 1, "Expect at least on arg for scanf"
        self.args = args

    def __str__(self):
        return f"FileScanFormat({self.file}, {self._format}, {self.args})"

    def retarget(self, new_circuit, clock):
        return FileScanFormat(self.file, self._format, self.args)


class Var(Action, expression.Expression):
    def __init__(self, name, _type):
        super().__init__()
        self.name = name
        self._type = _type

    def __str__(self):
        return f"Var({self.name}, {self._type})"

    def retarget(self, new_circuit, clock):
        return Var(self.name, self._type)


class Assert(Action):
    def __init__(self, expr):
        self.expr = expr

    def __str__(self):
        return f"Assert({self.expr})"

    def retarget(self, new_circuit, clock):
        return Assert(self.expr)
