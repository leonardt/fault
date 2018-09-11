from abc import ABC, abstractmethod


class Action(ABC):
    pass


class Poke(Action):
    def __init__(self, port, value):
        super().__init__()
        if port.isinput():
            raise ValueError(f"Can only poke inputs: {port} {type(port)}")
        self.port = port
        self.value = value

    def __str__(self):
        return f"Poke({self.port.debug_name}, {self.value})"


class Expect(Action):
    def __init__(self, port, value):
        super().__init__()
        if port.isoutput():
            raise ValueError(f"Can only expect on outputs: {port} {type(port)}")
        self.port = port
        self.value = value

    def __str__(self):
        return f"Expect({self.port.debug_name}, {self.value})"


class Eval(Action):
    def __init__(self):
        super().__init__()

    def __str__(self):
        return f"Eval()"


class Step(Action):
    def __init__(self, steps, clock):
        super().__init__()
        self.steps = steps
        self.clock = clock

    def __str__(self):
        return f"Step({self.steps}, {self.clock.debug_name})"
