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
    def __init__(self, port, format_str="%x"):
        super().__init__()
        self.port = port
        self.format_str = format_str

    def __str__(self):
        return f"Print({self.port.debug_name}, \"{self.format_str}\")"

    def retarget(self, new_circuit, clock):
        cls = type(self)
        new_port = new_circuit.interface.ports[str(self.port.name)]
        return cls(new_port, self.format_str)


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
