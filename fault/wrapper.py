import fault
from fault.select_path import SelectPath


class Wrapper:
    def __init__(self, circuit, parent):
        self.circuit = circuit
        self.instance_map = {instance.name: instance for instance in
                             circuit.instances}
        self.parent = parent

    def __setattr__(self, attr, value):
        # Hack to stage this after __init__ has been run, should redefine this
        # method in a metaclass? Could also use a try/except pattern, so the
        # exceptions only occur during object instantiation
        if hasattr(self, "circuit") and hasattr(self, "instance_map"):
            if attr in self.circuit.interface.ports.keys():
                if isinstance(self.parent, fault.Tester):
                    self.parent.poke(self.circuit.interface.ports[attr], value)
                else:
                    exit(1)
            else:
                object.__setattr__(self, attr, value)
        else:
            object.__setattr__(self, attr, value)

    def __getattr__(self, attr):
        # Hack to stage this after __init__ has been run, should redefine this
        # method in a metaclass?
        try:
            if attr in self.circuit.interface.ports.keys():
                return PortWrapper(self.circuit.interface.ports[attr], self)
            elif attr in self.instance_map:
                return InstanceWrapper(self.instance_map[attr], self)
            else:
                object.__getattribute__(self, attr)
        except Exception as e:
            object.__getattribute__(self, attr)


class CircuitWrapper(Wrapper):
    pass


class PortWrapper:
    def __init__(self, port, parent):
        self.port = port
        self.parent = parent

    def expect(self, value):
        select_path = self.select_path
        select_path.tester.expect(select_path, value)

    @property
    def select_path(self):
        select_path = SelectPath([self.port])
        parent = self.parent
        while not isinstance(parent, fault.Tester):
            select_path.insert(0, parent)
            parent = parent.parent
        select_path.tester = parent
        return select_path


class InstanceWrapper(Wrapper):
    def __init__(self, instance, parent):
        self.instance = instance
        super().__init__(type(instance), parent)
