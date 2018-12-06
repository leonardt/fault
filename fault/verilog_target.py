from abc import abstractmethod
import magma as m
from fault.target import Target
from pathlib import Path
import fault.actions as actions
from fault.util import flatten


def verilog_name(name):
    if isinstance(name, m.ref.DefnRef):
        return str(name)
    if isinstance(name, m.ref.ArrayRef):
        array_name = verilog_name(name.array.name)
        return f"{array_name}_{name.index}"
    if isinstance(name, m.ref.TupleRef):
        tuple_name = verilog_name(name.tuple.name)
        return f"{tuple_name}_{name.index}"
    raise NotImplementedError(name, type(name))


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

    @classmethod
    def generate_array_action_code(cls, i, action):
        result = []
        for j in range(action.port.N):
            if isinstance(action, actions.Print):
                value = action.format_str
            else:
                value = action.value[j]
            result += [
                cls.generate_action_code(
                    i, type(action)(action.port[j], value)
                )]
        return flatten(result)

    @classmethod
    def generate_action_code(cls, i, action):
        if isinstance(action, (actions.PortAction, actions.Print)) and \
                isinstance(action.port, m.ArrayType) and \
                not isinstance(action.port.T, m.BitKind):
            return cls.generate_array_action_code(i, action)
        if isinstance(action, actions.Poke):
            return cls.make_poke(i, action)
        if isinstance(action, actions.Print):
            name = verilog_name(action.port.name)
            return cls.make_print(i, action)
        if isinstance(action, actions.Expect):
            return cls.make_expect(i, action)
        if isinstance(action, actions.Eval):
            return cls.make_eval(i, action)
        if isinstance(action, actions.Step):
            return cls.make_step(i, action)
        raise NotImplementedError(action)

    @classmethod
    @abstractmethod
    def make_poke(cls, i, action):
        pass

    @classmethod
    @abstractmethod
    def make_print(cls, i, action):
        pass

    @classmethod
    @abstractmethod
    def make_expect(cls, i, action):
        pass

    @classmethod
    @abstractmethod
    def make_eval(cls, i, action):
        pass

    @classmethod
    @abstractmethod
    def make_step(cls, i, action):
        pass
