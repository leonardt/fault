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

    def __setattr__(self, attr, value):
        # Hack to stage this after __init__ has been run, should redefine this
        # method in a metaclass? Could also use a try/except pattern, so the
        # exceptions only occur during object instantiation
        if hasattr(self, "circuit") and hasattr(self, "instance_map"):
            if attr in self.circuit.interface.ports.keys():
                if isinstance(self.parent, fault.Tester):
                    self.parent.poke(self.circuit.interface.ports[attr], value)
                else:
                    raise NotImplementedError()
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
        self.init_done = True

    def expect(self, value):
        select_path = self.select_path
        select_path.tester.expect(select_path, value)

    def __setitem__(self, key, value):
        if not isinstance(self.port, (m.ArrayType, m.TupleType)):
            raise Exception(f"Can only use item assignment with arrays and "
                            f"tuples not {type(self.port)}")
        select_path = self.select_path
        select_path[-1] = select_path[-1][key]
        select_path.tester.poke(select_path, value)

    def __getitem__(self, key):
        if not isinstance(self.port, (m.ArrayType, m.TupleType)):
            raise Exception(f"Can only use getitem with arrays and "
                            f"tuples not {type(self.port)}")
        select_path = self.select_path
        return PortWrapper(self.port[key], self.parent)

    def __getattr__(self, key):
        try:
            object.__getattribute__(self, "init_done")
            if not isinstance(self.port, (m.TupleType)):
                raise Exception(f"Can only use getattr with tuples, "
                                f"not {type(self.port)}")
            select_path = self.select_path
            return PortWrapper(getattr(self.port, key), self.parent)
        except AttributeError:
            return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
        try:
            object.__getattribute__(self, "init_done")
            if not isinstance(self.port, (m.TupleType)):
                raise Exception(f"Can only use setattr with tuples, "
                                f"not {type(self.port)}")
            select_path = self.select_path
            select_path.tester.poke(getattr(self.port, key), value)
        except AttributeError:
            return object.__setattr__(self, key, value)

    @property
    def select_path(self):
        select_path = SelectPath([self.port])
        parent = self.parent
        while not isinstance(parent, fault.Tester):
            select_path.insert(0, parent)
            parent = parent.parent
        select_path.tester = parent
        return select_path

    def __and__(self, other):
        return expression.And(self, other)

    def __eq__(self, other):
        return expression.EQ(self, other)

    def __ne__(self, other):
        return expression.NE(self, other)

    def __lt__(self, other):
        return expression.LT(self, other)

    def __le__(self, other):
        return expression.LE(self, other)

    def __gt__(self, other):
        return expression.GT(self, other)

    def __ge__(self, other):
        return expression.GE(self, other)

    def __add__(self, other):
        return expression.Add(self, other)

    def __invert__(self):
        return expression.Invert(self)

    def __lshift__(self, other):
        return expression.LShift(self, other)

    def __rshift__(self, other):
        return expression.RShift(self, other)

    def __mod__(self, other):
        return expression.Mod(self, other)

    def __mul__(self, other):
        return expression.Mul(self, other)

    def __neg__(self):
        return expression.Neg(self)

    def __pos__(self):
        return expression.Pos(self)

    def __pow__(self, other):
        return expression.Pow(self, other)

    def __sub__(self, other):
        return expression.Sub(self, other)

    def __truediv__(self, other):
        return expression.Div(self, other)

    def __or__(self, other):
        return expression.Or(self, other)

    def __xor__(self, other):
        return expression.XOr(self, other)


class InstanceWrapper(Wrapper):
    def __init__(self, instance, parent):
        self.instance = instance
        super().__init__(type(instance), parent)
        self.init_done = True

    def __setattr__(self, attr, value):
        try:
            object.__getattribute__(self, "init_done")
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
                            "outReg", self.instance_map[attr].O),
                        InstanceWrapper(self.instance_map[attr], self))
                    select_path = wrapper.select_path
                    select_path.tester.poke(select_path, value)
                except Exception as e:
                    print(e)
                    exit(1)
            else:
                raise Exception(f"Could not set attr {attr} with value"
                                f" {value}")
        except AttributeError:
            object.__setattr__(self, attr, value)
