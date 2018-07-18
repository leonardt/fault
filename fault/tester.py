from bit_vector import BitVector
import magma as m
import functools
import magma.testing.verilator


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
        self.clock_index = None
        for i, (key, value) in enumerate(self.ports.items()):
            self.port_index_mapping[value] = i
            if value is clock:
                self.clock_index = i
        # Initialize first test vector to all Nones
        self.test_vectors.append(
            [BitVector(None, 1 if isinstance(port, m._BitType) else len(port))
             for port in self.ports.values()])

    def get_index(self, port):
        return self.port_index_mapping[port]

    @convert_value
    def poke(self, port, value):
        if port.isinput():
            raise ValueError(f"Can only poke an input: {port} {type(port)}")
        self.test_vectors[-1][self.get_index(port)] = value

    @convert_value
    def expect(self, port, value):
        if port.isoutput():
            raise ValueError(f"Can only expect an output: {port} {type(port)}")
        self.test_vectors[-1][self.get_index(port)] = value

    def eval(self):
        self.test_vectors.append(self.test_vectors[-1][:])

    def step(self):
        if self.clock_index is None:
            raise RuntimeError(
                "Stepping tester without a clock (did you specify a clock "
                "during initialization?)"
            )
        self.eval()
        self.test_vectors[-1][self.clock_index] ^= BitVector(1, 1)

    def compile_and_run(self, directory="build", target="verilator", flags=[]):
        if target == "verilator":
            magma.testing.verilator.compile(
                f"{directory}/test_{self.circuit.name}.cpp", self.circuit,
                self.test_vectors)
            magma.testing.verilator.run_verilator_test(
                self.circuit.name, f"test_{self.circuit.name}",
                self.circuit.name, flags, build_dir=directory)
        else:
            raise NotImplementedError(target)
