from abc import ABC, abstractmethod
import fault
from fault.select_path import SelectPath


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
        new_port = new_circuit.interface.ports[str(self.port.name)]
        return cls(new_port, self.value)


def is_input(port):
    if isinstance(port, SelectPath):
        port = port[-1]
    if isinstance(port, fault.WrappedVerilogInternalPort):
        return port.type_.isinput()
    else:
        return port.isinput()


class Poke(PortAction):
    def __init__(self, port, value):
        if is_input(port):
            raise ValueError(f"Can only poke inputs: {port.debug_name} "
                             f"{type(port)}")
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


def is_output(port):
    if isinstance(port, SelectPath):
        port = port[-1]
    if isinstance(port, fault.WrappedVerilogInternalPort):
        return not port.type_.isoutput()
    else:
        return not port.isoutput()


class Expect(PortAction):
    def __init__(self, port, value):
        super().__init__(port, value)


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


class Peek(Action):
    def __init__(self, port):
        super().__init__()
        if not is_output(port):
            raise ValueError(f"Can only peek on outputs: {port.debug_name} "
                             f"{type(port)}")
        self.port = port

    def retarget(self, new_circuit, clock):
        cls = type(self)
        new_port = new_circuit.interface.ports[str(self.port.name)]
        return cls(new_port)

    def __eq__(self, other):
        return self.port == other.port

    def __str__(self):
        return f"Peek({self.port.debug_name})"


class Eval(Action):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return "Eval()"

    def retarget(self, new_circuit, clock):
        return Eval()


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
    def __init__(self, n_iter, loop_var, actions):
        self.n_iter = n_iter
        self.actions = actions
        self.loop_var = loop_var

    def __str__(self):
        # TODO: Might be nice to format this print output over multiple lines
        # for actions
        return f"Loop({self.n_iter}, {self.loop_var}, {self.actions})"

    def retarget(self, new_circuit, clock):
        actions = [action.retarget(new_circuit, clock) for action in
                   self.actions]
        return Loop(self.n_iter, actions)


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
