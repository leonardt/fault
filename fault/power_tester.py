import magma as m
from fault import Tester


class PowerTester(Tester):
    def __init__(self, circuit: m.Circuit, clock: m.Clock = None):
        super().__init__(circuit, clock)
        self.supply0s = []
        self.supply1s = []
        self.tris = []

    def add_power(self, port):
        self.supply1s.append(port.name.name)

    def add_ground(self, port):
        self.supply0s.append(port.name.name)

    def add_tri(self, port):
        self.tris.append(port.name.name)

    def run(self, target="system-verilog"):
        power_args = {
            "supply0s": self.supply0s,
            "supply1s": self.supply1s,
            "tris": self.tris,
        }
        self.targets[target].run(self.actions, power_args)
