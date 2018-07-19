from .target import Target
import magma.testing.verilator


class VerilatorTarget(Target):
    def __init__(self, circuit, test_vectors, directory="build/", flags=[]):
        super().__init__(circuit, test_vectors)
        self._directory = directory
        self._flags = flags

    def run(self):
        magma.testing.verilator.compile(
            f"{self._directory}/test_{self._circuit.name}.cpp", self._circuit,
            self._test_vectors)
        magma.testing.verilator.run_verilator_test(
            self._circuit.name, f"test_{self._circuit.name}",
            self._circuit.name, self._flags, build_dir=self._directory)
