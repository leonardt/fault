import magma as m
from fault.target import Target
from pathlib import Path


class VerilogTarget(Target):
    """
    Provides reuseable target logic for compiling circuits into verilog files.
    """
    def __init__(self, circuit, circuit_name=None, directory="build/",
                 skip_compile=False, magma_output="verilog"):
        super().__init__(circuit)

        if circuit_name is None:
            self.circuit_name = self.circuit.name
        else:
            self.circuit_name = circuit_name

        self.directory = Path(directory)

        self.skip_compile = skip_compile

        self.magma_output = magma_output

        self.verilog_file = self.directory / Path(f"{self.circuit_name}.v")
        # Optionally compile this module to verilog first.
        if not self.skip_compile:
            prefix = str(self.verilog_file)[:-2]
            m.compile(prefix, self.circuit, output=self.magma_output)
            if not self.verilog_file.is_file():
                raise Exception(f"Compiling {self.circuit} failed")
