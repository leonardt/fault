from bit_vector import BitVector
import magma as m
import functools
from .verilator_target import VerilatorTarget
from fault.array import Array
import copy


def convert_value(fn):
    @functools.wraps(fn)
    def wrapped(self, port, value):
        if isinstance(port, m.ArrayType) and isinstance(value, int):
            value = BitVector(value, len(port))
        elif isinstance(port, m._BitType) and isinstance(value, int):
            value = BitVector(value, 1)
        return fn(self, port, value)
    return wrapped


class Tester:
    def __init__(self, circuit, clock=None):
        self.circuit = circuit
        self.test_vectors = []
        self.port_index_mapping = {}
        self.ports = self.circuit.interface.ports
        self.clock = clock
        self.clock_index = None
        for i, (key, value) in enumerate(self.ports.items()):
            self.port_index_mapping[value] = i
            if value is clock:
                self.clock_index = i
        # Initialize first test vector to all Nones
        initial_vector = []
        for port in self.ports.values():
            val = self.get_initial_value(port)
            initial_vector.append(val)
        self.test_vectors.append(initial_vector)

    def get_initial_value(self, port):
        if isinstance(port, m._BitType):
            return BitVector(None, 1)
        elif isinstance(port, m.ArrayType):
            return self.get_array_val(port)
        else:
            raise NotImplementedError(port)

    def get_array_val(self, arr, val=None):
        if isinstance(arr.T, m._BitKind):
            val = BitVector(val, len(arr))
        elif isinstance(arr, m.ArrayType) and isinstance(arr.T, m.ArrayKind):
            val = Array([self.get_array_val(x) for x in arr], len(arr))
        else:
            raise NotImplementedError(arr, type(arr), arr.T)
        return val

    def get_index(self, port):
        return self.port_index_mapping[port]

    def add_test_vector(self, port, value):
        if isinstance(port.name, m.ref.ArrayRef):
            parent = port
            indices = []
            # Get the outer most port
            while isinstance(parent.name, m.ref.ArrayRef):
                indices.insert(0, parent.name.index)
                parent = parent.name.array
            vector = self.test_vectors[-1][self.get_index(parent)]
            for idx in indices[:-1]:
                vector = vector[idx]
            vector[indices[-1]] = value
        else:
            self.test_vectors[-1][self.get_index(port)] = value

    @convert_value
    def poke(self, port, value):
        if port.isinput():
            raise ValueError(f"Can only poke an input: {port} {type(port)}")
        self.add_test_vector(port, value)

    @convert_value
    def expect(self, port, value):
        if port.isoutput():
            raise ValueError(f"Can only expect an output: {port} {type(port)}")
        self.add_test_vector(port, value)

    def eval(self):
        """
        Finalize the current test vector by making a copy
        For the new test vector,
            (1) Set all inputs to retain their previous value
            (2) Set all expected outputs to None (X) for the new test vector
        """
        self.test_vectors.append(copy.deepcopy(self.test_vectors[-1]))
        for port in self.ports.values():
            if port.isinput():
                self.test_vectors[-1][self.get_index(port)] = \
                    self.get_initial_value(port)

    def step(self):
        if self.clock_index is None:
            raise RuntimeError(
                "Stepping tester without a clock (did you specify a clock "
                "during initialization?)"
            )
        self.eval()
        self.test_vectors[-1][self.clock_index] ^= BitVector(1, 1)

    def compile_and_run(self, target="verilator", **kwargs):
        if target == "verilator":
            target = VerilatorTarget(self.circuit, self.test_vectors, **kwargs)
        else:
            raise NotImplementedError(target)

        target.run()

    def zero_inputs(self):
        for port in self.ports.values():
            if port.isoutput():
                val = 0
                if isinstance(port, m.ArrayType):
                    val = self.get_array_val(port, 0)
                self.poke(port, val)
