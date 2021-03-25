import magma as m
from typing import List


class LoopIndex:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class NoClockInit:
    """
    Sub testers should not initialize the clock
    """

    def init_clock(self):
        pass


def add_control_structures(tester_class):
    """
    Decorator to add control structures after Tester class definition so we can
    use the definition as a base class.

    This allows Loops, If, and Else testers to inherit the base class methods
    (e.g. for SynchronousTester they should inherit the advance_cycle method)
    """
    class LoopTester(NoClockInit, tester_class):
        __unique_index_id = -1

        def __init__(self, circuit: m.Circuit, clock: m.Clock, monitors):
            super().__init__(circuit, clock, monitors=monitors)
            LoopTester.__unique_index_id += 1
            self.index = LoopIndex(
                f"__fault_loop_var_action_{LoopTester.__unique_index_id}")

    class ElseTester(NoClockInit, tester_class):
        def __init__(self, else_actions: List, circuit: m.Circuit,
                     clock: m.Clock, monitors):
            super().__init__(circuit, clock, monitors=monitors)
            self.actions = else_actions

    class IfTester(NoClockInit, tester_class):
        def __init__(self, circuit: m.Circuit, clock: m.Clock, monitors):
            super().__init__(circuit, clock, monitors=monitors)
            self.else_actions = []

        def _else(self):
            return ElseTester(self.else_actions, self._circuit, self.clock,
                              self.monitors)

    class ForkTester(NoClockInit, tester_class):
        def __init__(self, name, circuit: m.Circuit, clock: m.Clock, monitors):
            super().__init__(circuit, clock, monitors=monitors)
            self.name = name

    tester_class.LoopTester = LoopTester
    tester_class.ElseTester = ElseTester
    tester_class.IfTester = IfTester
    tester_class.ForkTester = ForkTester
    return tester_class
