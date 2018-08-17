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


class Expect(Action):
    def __init__(self, port, value):
        super().__init__()
        if port.isoutput():
            raise ValueError(f"Can only expect on outputs: {port} {type(port)}")
        self.port = port
        self.value = value


class Eval(Action):
    def __init__(self):
        super().__init__()


class Step(Action):
    def __init__(self, steps, clock):
        super().__init__()
        self.steps = steps
        self.clock = clock
