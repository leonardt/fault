from bit_vector import BitVector
import magma as m
from magma.simulator.python_simulator import PythonSimulator
from magma.simulator.coreir_simulator import CoreIRSimulator
import fault.actions as actions
from fault.logging import warning
from fault.target import Target


class MagmaSimulatorTarget(Target):
    def __init__(self, circuit, actions, clock=None, backend="coreir"):
        super().__init__(circuit, actions)
        self.clock = clock
        self.backend_cls = MagmaSimulatorTarget.simulator_cls(backend)

    def simulator_cls(backend):
        if backend == "coreir":
            return CoreIRSimulator
        if backend == "python":
            warning("Python simulator is not actively supported")
            return PythonSimulator
        raise NotImplementedError(backend)

    def run(self):
        simulator = self.backend_cls(self.circuit, self.clock)
        for action in self.actions:
            if isinstance(action, actions.Poke):
                value = action.value
                # Python simulator does not support setting Bit with
                # BitVector(1), so do conversion here
                if isinstance(action.port, m.BitType) and \
                        isinstance(value, BitVector):
                    value = value.as_uint()
                simulator.set_value(action.port, value)
            elif isinstance(action, actions.Expect):
                got = BitVector(simulator.get_value(action.port))
                expected = action.value
                assert got == expected, f"Got {got}, expected {expected}"
            elif isinstance(action, actions.Eval):
                simulator.evaluate()
            elif isinstance(action, actions.Step):
                if self.clock is not action.clock:
                    raise RuntimeError(f"Using different clocks: {self.clock}, "
                                       f"{action.clock}")
                simulator.advance_cycle(action.steps)
            else:
                raise NotImplementedError(action)
