from abc import abstractmethod
import magma as m
from fault.target import Target
from pathlib import Path
import fault.actions as actions
from fault.util import flatten
import os
from fault.select_path import SelectPath
from fault.verilog_utils import verilog_name


class VerilogTarget(Target):
    """
    Provides reuseable target logic for compiling circuits into verilog files.
    """
    def __init__(self, circuit, circuit_name=None, directory="build/",
                 skip_compile=False, include_verilog_libraries=[],
                 magma_output="verilog", magma_opts={}):
        super().__init__(circuit)

        if circuit_name is None:
            self.circuit_name = self.circuit.name
        else:
            self.circuit_name = circuit_name

        self.directory = Path(directory)
        os.makedirs(directory, exist_ok=True)

        self.skip_compile = skip_compile

        self.include_verilog_libraries = include_verilog_libraries

        self.magma_output = magma_output
        self.magma_opts = magma_opts

        if hasattr(circuit, "verilog_file_name") and \
                os.path.splitext(circuit.verilog_file_name)[-1] == ".sv":
            suffix = "sv"
        else:
            suffix = "v"
        self.verilog_file = Path(f"{self.circuit_name}.{suffix}")
        # Optionally compile this module to verilog first.
        if not self.skip_compile:
            prefix = os.path.splitext(self.directory / self.verilog_file)[0]
            m.compile(prefix, self.circuit, output=self.magma_output,
                      **self.magma_opts)
            if not (self.directory / self.verilog_file).is_file():
                raise Exception(f"Compiling {self.circuit} failed")

        self.assumptions = []
        self.guarantees = []

    def make_assume(self, i, action):
        self.assumptions.append(action)
        return ""

    def make_guarantee(self, i, action):
        self.guarantees.append(action)
        return ""

    def generate_array_action_code(self, i, action):
        result = []
        port = action.port
        if isinstance(port, SelectPath):
            port = port[-1]
        for j in range(port.N):
            if isinstance(action, actions.Print):
                value = action.format_str
            else:
                value = action.value[j]
            result += [
                self.generate_action_code(
                    i, type(action)(port[j], value)
                )]
        return flatten(result)

    def generate_action_code(self, i, action):
        if isinstance(action, (actions.PortAction)) and \
                isinstance(action.port, m.ArrayType) and \
                not isinstance(action.port.T, m.BitKind):
            return self.generate_array_action_code(i, action)
        elif isinstance(action, (actions.PortAction)) and \
                isinstance(action.port, SelectPath) and \
                isinstance(action.port[-1], m.ArrayType) and \
                not isinstance(action.port[-1].T, m.BitKind):
            return self.generate_array_action_code(i, action)
        if isinstance(action, actions.Poke):
            return self.make_poke(i, action)
        if isinstance(action, actions.Print):
            return self.make_print(i, action)
        if isinstance(action, actions.Expect):
            return self.make_expect(i, action)
        if isinstance(action, actions.Eval):
            return self.make_eval(i, action)
        if isinstance(action, actions.Step):
            return self.make_step(i, action)
        if isinstance(action, actions.Assume):
            return self.make_assume(i, action)
        if isinstance(action, actions.Guarantee):
            return self.make_guarantee(i, action)
        if isinstance(action, actions.Loop):
            return self.make_loop(i, action)
        if isinstance(action, actions.FileOpen):
            return self.make_file_open(i, action)
        if isinstance(action, actions.FileWrite):
            return self.make_file_write(i, action)
        if isinstance(action, actions.FileRead):
            return self.make_file_read(i, action)
        if isinstance(action, actions.FileClose):
            return self.make_file_close(i, action)
        raise NotImplementedError(action)

    @abstractmethod
    def make_poke(self, i, action):
        pass

    @abstractmethod
    def make_print(self, i, action):
        pass

    @abstractmethod
    def make_expect(self, i, action):
        pass

    @abstractmethod
    def make_eval(self, i, action):
        pass

    @abstractmethod
    def make_step(self, i, action):
        pass

    @abstractmethod
    def make_loop(self, i, action):
        pass

    @abstractmethod
    def make_file_open(self, i, action):
        pass

    @abstractmethod
    def make_file_close(self, i, action):
        pass

    @abstractmethod
    def make_file_read(self, i, action):
        pass

    @abstractmethod
    def make_file_write(self, i, action):
        pass
