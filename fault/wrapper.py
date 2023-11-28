import fault
from fault.select_path import SelectPath
import fault.expression as expression
import magma as m


class Wrapper:
    def __init__(self, circuit, parent):
        self.circuit = circuit
        if hasattr(circuit, "instances"):
            self.instance_map = {instance.name: instance for instance in
                                 circuit.instances}
        else:
            self.instance_map = None
        self.parent = parent
        self.init_done = True

    def __setattr__(self, attr, value):
        # Hack to stage this after __init__ has been run, should redefine this
        # method in a metaclass? Could also use a try/except pattern, so the
        # exceptions only occur during object instantiation
        try:
            init_done = object.__getattribute__(self, "init_done")
        except AttributeError:
            init_done = False

        if not init_done:
            object.__setattr__(self, attr, value)
            return

        if hasattr(self, "circuit") and hasattr(self, "instance_map"):
            if attr in self.circuit.interface.ports.keys():
                if isinstance(self.parent, fault.TesterBase):
                    self.parent.poke(self.circuit.interface.ports[attr], value)
                else:
                    raise NotImplementedError()
            else:
                raise AttributeError(f"{attr} is not a valid port")
        else:
            raise AttributeError(f"{attr} is not a valid port")

    def __getattr__(self, attr):
        # Hack to stage this after __init__ has been run, should redefine this
        # method in a metaclass?
        try:
            init_done = object.__getattribute__(self, "init_done")
        except AttributeError:
            init_done = False

        if init_done:
            if attr in self.circuit.interface.ports.keys():
                return PortWrapper(self.circuit.interface.ports[attr], self)
            elif attr in self.instance_map:
                return InstanceWrapper(self.instance_map[attr], self)
        return object.__getattribute__(self, attr)


class CircuitWrapper(Wrapper):
    pass


class PortWrapper(expression.Expression):
    def __init__(self, port, parent):
        self.port = m.protocol_type.magma_value(port)
        self.parent = parent
        self.init_done = True

    def expect(self, value, msg=None):
        select_path = self.select_path
        select_path.tester.expect(select_path, value, msg=msg)

    def __setitem__(self, key, value):
        if not isinstance(self.port, (m.Array, m.Tuple)):
            raise Exception(f"Can only use item assignment with arrays and "
                            f"tuples not {type(self.port)}")
        select_path = self.select_path
        select_path[-1] = select_path[-1][key]
        select_path.tester.poke(select_path, value)

    def __getitem__(self, key):
        if not isinstance(self.port, (m.Array, m.Tuple)):
            raise Exception(f"Can only use getitem with arrays and "
                            f"tuples not {type(self.port)}")
        select_path = self.select_path
        return PortWrapper(self.port[key], self.parent)

    def __getattr__(self, key):
        try:
            object.__getattribute__(self, "init_done")
        except AttributeError:
            return object.__getattribute__(self, key)
        if isinstance(self.port, m.Tuple):
            return PortWrapper(getattr(self.port, key), self.parent)
        return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
        try:
            init_done = object.__getattribute__(self, "init_done")
        except AttributeError:
            init_done = False

        if init_done:
            if not isinstance(self.port, m.Tuple):
                raise Exception(f"Can only use setattr with tuples, "
                                f"not {type(self.port)}")
            select_path = self.select_path
            select_path.tester.poke(getattr(self.port, key), value)
        else:
            return object.__setattr__(self, key, value)

    @property
    def select_path(self):
        select_path = SelectPath([self.port])
        parent = self.parent
        while not isinstance(parent, fault.TesterBase):
            select_path.insert(0, parent)
            parent = parent.parent
        select_path.tester = parent
        return select_path


class InstanceWrapper(Wrapper):
    def __init__(self, instance, parent):
        self.instance = instance
        super().__init__(type(instance), parent)

    def __setattr__(self, attr, value):
        try:
            init_done = object.__getattribute__(self, "init_done")
        except AttributeError:
            init_done = False

        if init_done:
            if attr in self.circuit.interface.ports.keys():
                wrapper = PortWrapper(self.circuit.interface.ports[attr], self)
                select_path = wrapper.select_path
                select_path.tester.poke(select_path, value)
            elif attr in self.instance_map and \
                    "reg_P" in type(self.instance_map[attr]).name:
                try:
                    # Support directly poking coreir reg
                    wrapper = PortWrapper(
                        fault.WrappedVerilogInternalPort(
                            "outReg", type(self.instance_map[attr].O)),
                        InstanceWrapper(self.instance_map[attr], self))
                    select_path = wrapper.select_path
                    select_path.tester.poke(select_path, value)
                except Exception as e:
                    print(e)
                    exit(1)
            else:
                raise Exception(f"Could not set attr {attr} with value"
                                f" {value}")
        else:
            object.__setattr__(self, attr, value)

    def set_definition(self, defn):
        self.instance.__class__ = defn
