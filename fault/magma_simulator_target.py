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

    @staticmethod
    def check(got, port, expected):
        if isinstance(port, m.ArrayType) and \
                isinstance(port.T, m._BitType) and \
                not isinstance(port, m.BitsType) and \
                isinstance(expected, BitVector):
            # If port is an Array(N, Bit) and **not** a Bits(N), then the
            # Python simulator will return a list of bools. So, if the user
            # provided a BitVector, we unpack it here so the equality check
            # works
            expected = expected.as_bool_list()
        if isinstance(port, m.ArrayType):
            for i in range(port.N):
                MagmaSimulatorTarget.check(got[i], port[i], expected[i])
            return
        assert got == expected, f"Got {got}, expected {expected}"

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
            elif isinstance(action, actions.Print):
                got = simulator.get_value(action.port)
                if isinstance(action.port, m.ArrayType) and \
                        isinstance(action.port.T, (m._BitType, m._BitKind)):
                    got = BitVector(got).as_uint()
                elif isinstance(action.port, m.ArrayType):
                    raise NotImplementedError("Printing complex nested arrays")
                print(f'{action.port.debug_name} = {action.format_str}' %
                      got)
            elif isinstance(action, actions.Expect):
                got = simulator.get_value(action.port)
                MagmaSimulatorTarget.check(got, action.port, action.value)
            elif isinstance(action, actions.Eval):
                simulator.evaluate()
            elif isinstance(action, actions.Step):
                if self.clock is not action.clock:
                    raise RuntimeError(f"Using different clocks: {self.clock}, "
                                       f"{action.clock}")
                simulator.advance_cycle(action.steps)
            else:
                raise NotImplementedError(action)
