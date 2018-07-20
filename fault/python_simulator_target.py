from .target import Target
from magma.testing.function import testvectors
import magma.config as config
import inspect
import os
import subprocess
import magma as m
from magma.simulator.python_simulator import PythonSimulator


class PythonSimulatorTarget(Target):
    def __init__(self, circuit, test_vectors, clock):
        super().__init__(circuit, test_vectors)
        self._clock = clock

    def run(self):
        ports = self._circuit.interface.ports
        simulator = PythonSimulator(self._circuit, self._clock)
        test_vector_length = len(self._test_vectors[0])
        assert len(ports.keys()) == test_vector_length
        clock_val = None
        for tv_index, tv in enumerate(self._test_vectors):
            for i, (name, port) in enumerate(ports.items()):
                val = tv[i]
                if port is self._clock:
                    if tv_index == 0:
                        clock_val = val
                    elif val != clock_val:
                        print("Advancing clock")
                        simulator.advance(2)
                elif port.isoutput():
                    print(f"Setting {self._circuit.name}.{name} to {val}")
                    simulator.set_value(port, val)
                elif port.isinput():
                    print(f"Asserting {self._circuit.name}.{name} is {val}")
                    sim_val = simulator.get_value(port)
                    assert sim_val == val
                else:
                    raise NotImplementedError()
