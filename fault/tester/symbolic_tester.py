import fault
from .staged_tester import Tester
from fault.wrapper import Wrapper, PortWrapper, InstanceWrapper
from fault.cosa_target import CoSATarget
import fault.actions as actions
from fault.random import ConstrainedRandomGenerator


class SymbolicWrapper(Wrapper):
    def __init__(self, circuit, parent):
        super().__init__(circuit, parent)

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
                return SymbolicPortWrapper(self.circuit.interface.ports[attr],
                                           self)
            elif attr in self.instance_map:
                return SymbolicInstanceWrapper(self.instance_map[attr], self)
            else:
                object.__getattribute__(self, attr)
        except Exception as e:
            object.__getattribute__(self, attr)


class SymbolicCircuitWrapper(SymbolicWrapper):
    pass


class SymbolicPortWrapper(PortWrapper):
    def assume(self, pred):
        select_path = self.select_path
        select_path.tester.assume(select_path, pred)

    def guarantee(self, pred):
        select_path = self.select_path
        select_path.tester.guarantee(select_path, pred)


class SymbolicInstanceWrapper(InstanceWrapper):
    pass


class SymbolicTester(Tester):
    def __init__(self, circuit, clock=None, num_tests=100,
                 random_strategy="rejection"):
        super().__init__(circuit, clock)
        self.num_tests = num_tests
        self.random_strategy = random_strategy

    def assume(self, port, constraint):
        """
        Place a constraint on an input port by providing a symbolic expression
        as a Python lambda or function

            symbolic_tester_inst.assume(top.I, lambda x : x >= 0)
        """
        action = actions.Assume(port, constraint)
        action.has_randvals = False
        if self.random_strategy == "smt":
            port = port[-1]
            v = {str(port.name): len(port)}
            gen = ConstrainedRandomGenerator()
            action.randvals = iter(gen(v, constraint, self.num_tests))
            action.has_randvals = True
        self.actions.append(action)

    def guarantee(self, port, constraint):
        """
        Assert a property about an output port by providing a symbolic
        expression as a Python lambda or function

            symbolic_tester_inst.assume(top.O, lambda x : x >= 0)
        """
        self.actions.append(actions.Guarantee(port, constraint))

    @property
    def circuit(self):
        return SymbolicCircuitWrapper(self._circuit, self)

    def run(self, target="verilator"):
        if target == "verilator":
            self.targets[target].run(self.actions, self.verilator_includes,
                                     self.num_tests, self._circuit)
        elif target == "cosa":
            self.targets[target].run(self.actions)
        else:
            raise NotImplementedError()

    def make_target(self, target: str, **kwargs):
        if target == "cosa":
            return CoSATarget(self._circuit, **kwargs)
        else:
            return super().make_target(target, **kwargs)
