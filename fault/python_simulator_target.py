import fault.logging
from .target import Target
from magma.simulator.python_simulator import PythonSimulator
from fault.array import Array


def convert_value(val):
    if isinstance(val, Array):
        return val.value
    return val


class PythonSimulatorTarget(Target):
    def __init__(self, circuit, test_vectors, clock):
        super().__init__(circuit, test_vectors)
        self._clock = clock
        self._simulator = None

    def init_simulator(self):
        self._simulator = PythonSimulator(self._circuit, self._clock)

    def __set_value(self, port, val):
        fault.logging.debug(f"Setting {self._circuit.name}.{port.name.name} to "
                            f"{val}")
        val = convert_value(val)
        self._simulator.set_value(port, val)

    def __check_value(self, port, expected_val):
        fault.logging.debug(f"Asserting {self._circuit.name}.{port.name.name} "
                            f"is {expected_val}")
        sim_val = self._simulator.get_value(port)
        expected_val = convert_value(expected_val)
        assert sim_val == expected_val

    def __parse_tv(self, tv):
        inputs = {}
        steps = 0
        outputs = {}
        ports = self._circuit.interface.ports
        for i, port in enumerate(ports.values()):
            val = tv[i]
            if val is None:
                continue
            if port is self._clock:
                if self._simulator.get_value(self._clock) != val:
                    steps += 1
            elif port.isoutput():
                inputs[port] = val
            elif port.isinput():
                outputs[port] = val
            else:
                raise NotImplementedError()
        return (inputs, steps, outputs)

    def __process_inputs(self, inputs):
        for port, val in inputs.items():
            self.__set_value(port, val)

    def __process_clock(self, steps):
        if steps == 0:
            return True
        self._simulator.advance(steps)
        return False

    def __process_outputs(self, outputs):
        for port, val in outputs.items():
            self.__check_value(port, val)

    def run(self):
        self.init_simulator()
        ports = self._circuit.interface.ports
        test_vector_length = len(self._test_vectors[0])
        assert len(ports.keys()) == test_vector_length, \
            "Expected len(test_vector) == len(ports.keys())"
        for tv in self._test_vectors:
            (inputs, steps, outputs) = self.__parse_tv(tv)
            self.__process_inputs(inputs)
            evaluate = self.__process_clock(steps)
            self.__process_outputs(outputs)
            if evaluate:
                self._simulator.evaluate()
