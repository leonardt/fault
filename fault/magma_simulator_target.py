from hwtypes import BitVector, Bit
import magma as m
from magma.simulator.python_simulator import PythonSimulator
from magma.simulator.coreir_simulator import CoreIRSimulator
from magma.scope import Scope
import fault.actions
from fault.target import Target
from .select_path import SelectPath
from .wrapper import PortWrapper


class MagmaSimulatorTarget(Target):
    def __init__(self, circuit, clock=None, backend="coreir"):
        super().__init__(circuit)
        self.clock = clock
        self.backend_cls = MagmaSimulatorTarget.simulator_cls(backend)

    def simulator_cls(backend):
        if backend == "coreir":
            return CoreIRSimulator
        if backend == "python":
            return PythonSimulator
        raise NotImplementedError(backend)

    def _make_print_str(self, format_str, values, simulator):
        got = [self.get_value(simulator, port) for port in values]
        format_values = ()
        for value, port in zip(got, values):
            if isinstance(port, m.Array) and \
                    issubclass(port.T, m.Digital):
                value = BitVector[len(port)](value).as_uint()
            elif isinstance(port, m.Array):
                raise NotImplementedError("Printing complex nested"
                                          " arrays")
            format_values += (value, )
        format_str = format_str.replace("\\n", "\n")
        return format_str % format_values

    def check(self, got, port, expected, msg, simulator):
        if isinstance(port, m.Array) and \
                isinstance(port.T, m.Digital) and \
                not isinstance(port, m.Bits) and \
                isinstance(expected, BitVector):
            # If port is an Array(N, Bit) and **not** a Bits(N), then the
            # Python simulator will return a list of bools. So, if the user
            # provided a BitVector, we unpack it here so the equality check
            # works
            expected = expected.as_bool_list()
        if isinstance(port, m.Array):
            for i in range(port.N):
                self.check(got[i], port[i], expected[i], msg, simulator)
            return
        error_msg = f"Got {got}, expected {expected}"
        equal = got == expected
        if not equal and msg is not None:
            if isinstance(msg, str):
                error_msg += "\n" + msg
            else:
                assert isinstance(msg, tuple)
                error_msg += "\n" + self._make_print_str(msg[0], msg[1:],
                                                         simulator)
        assert equal, error_msg

    def process_port(self, port):
        scope = Scope()
        if isinstance(port, fault.actions.Peek):
            port = port.port
        if isinstance(port, PortWrapper):
            port = port.select_path
        if isinstance(port, SelectPath):
            for i in port[1:-1]:
                scope = Scope(parent=scope, instance=i.instance)
            port = port[-1]
        return port, scope

    def set_value(self, simulator, port, value):
        port, scope = self.process_port(port)
        if isinstance(value, Bit):
            value = bool(value)
        simulator.set_value(port, value, scope)

    def get_value(self, simulator, port):
        port, scope = self.process_port(port)
        if isinstance(port, (int, BitVector, Bit, list)):
            return port
        return simulator.get_value(port, scope)

    def run(self, actions):
        simulator = self.backend_cls(self.circuit, self.clock)
        for action in actions:
            if isinstance(action, fault.actions.Poke):
                value = action.value
                # Python simulator does not support setting Bit with
                # BitVector(1), so do conversion here
                if isinstance(action.port, m.Digital) and \
                        isinstance(value, BitVector):
                    value = value.as_uint()
                self.set_value(simulator, action.port, value)
            elif isinstance(action, fault.actions.Print):
                print(self._make_print_str(action.format_str, action.ports,
                                           simulator),
                      end="")
            elif isinstance(action, fault.actions.Expect):
                got = self.get_value(simulator, action.port)
                expected = self.get_value(simulator, action.value)
                self.check(got, action.port, expected, action.msg, simulator)
            elif isinstance(action, fault.actions.Eval):
                simulator.evaluate()
            elif isinstance(action, fault.actions.Step):
                if self.clock is not action.clock:
                    raise RuntimeError(f"Using different clocks: {self.clock}, "
                                       f"{action.clock}")
                simulator.evaluate()
                simulator.advance(action.steps)
            else:
                raise NotImplementedError(action)
