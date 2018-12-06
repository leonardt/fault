from fault.verilog_target import VerilogTarget, verilog_name
import magma as m
from pathlib import Path
import fault.actions as actions
from bit_vector import BitVector
import fault.value_utils as value_utils
import subprocess


src_tpl = """\
module {circuit_name}_tb;
{declarations}
    initial begin
{initial_body}
        #20 $finish;
    end

    {circuit_name} dut (
        {port_list}
    );

endmodule
"""

ncsim_cmd_string = """\
database -open -vcd vcddb -into verilog.vcd -default -timescale ps
probe -create -all -vcd -depth all
run 10000ns
quit
"""


class SystemVerilogTarget(VerilogTarget):
    def __init__(self, circuit, circuit_name=None, directory="build/",
                 skip_compile=False, magma_output="coreir-verilog",
                 simulator=None, timescale="1ns/1ns", clock_step_delay=5):
        """
        circuit: a magma circuit

        circuit_name: the name of the circuit (default is circuit.name)

        directory: directory to use for generating collateral, buildling, and
                   running simulator

        skip_compile: (boolean) whether or not to compile the magma circuit

        magma_output: Set the output parameter to m.compile
                      (default coreir-verilog)

        simulator: "ncsim" or "vcs"

        timescale: Set the timescale for the verilog simulation
                   (default 1ns/1ns)

        clock_step_delay: Set the number of steps to delay for each step of the
                          clock
        """
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         magma_output)
        if simulator is None:
            raise ValueError("Must specify simulator when using system-verilog"
                             " target")
        if simulator not in ["vcs", "ncsim"]:
            raise ValueError(f"Unsupported simulator {simulator}")
        self.simulator = simulator
        self.timescale = timescale
        self.clock_step_delay = clock_step_delay

    def make_poke(self, i, action):
        name = verilog_name(action.port.name)
        if isinstance(action.value, BitVector) and \
                action.value.num_bits > 32:
            raise NotImplementedError()
        else:
            value = action.value
            if isinstance(action.port, m.SIntType) and value < 0:
                # Handle sign extension for verilator since it expects and
                # unsigned c type
                port_len = len(action.port)
                value = BitVector(value, port_len).as_uint()
            return [f"{name} = {value};", f"#{self.clock_step_delay}"]

    def make_print(self, i, action):
        name = verilog_name(action.port.name)
        return [f'$display("{action.port.debug_name} = '
                f'{action.format_str}", {name});']

    def make_expect(self, i, action):
        if value_utils.is_any(action.value):
            return []
        name = verilog_name(action.port.name)
        value = action.value
        if isinstance(value, actions.Peek):
            value = f"{value.port.name}"
        elif isinstance(action.port, m.SIntType) and value < 0:
            # Handle sign extension for verilator since it expects and
            # unsigned c type
            port_len = len(action.port)
            value = BitVector(value, port_len).as_uint()

        return [f"if ({name} != {value}) $error(\"Failed on action={i}"
                f" checking port {action.port.name}. Expected %x, got %x\""
                f", {value}, {name});"]

    def make_eval(self, i, action):
        # Eval implicit in SV simulations
        return []

    def make_step(self, i, action):
        name = verilog_name(action.clock.name)
        code = []
        for step in range(action.steps):
            code.append(f"#5 {name} ^= 1;")
        return code

    @staticmethod
    def generate_recursive_port_code(name, type_):
        declarations = ""
        port_list = []
        if isinstance(type_, m.ArrayKind):
            for j in range(type_.N):
                result = SystemVerilogTarget.generate_port_code(
                    name + "_" + str(j), type_.T
                )
                declarations += result[0]
                port_list.extend(result[1])
        elif isinstance(type_, m.TupleKind):
            for k, t in zip(type_.Ks, type_.Ts):
                result = SystemVerilogTarget.generate_port_code(
                    name + "_" + str(k), t
                )
                declarations += result[0]
                port_list.extend(result[1])
        return declarations, port_list

    @staticmethod
    def generate_port_code(name, type_):
        if (isinstance(type_, m.ArrayKind) and
                not isinstance(type_.T, m.BitKind)) or \
                isinstance(type_, m.TupleKind):
            return SystemVerilogTarget.generate_recursive_port_code(name, type_)
        else:
            width_str = ""
            if isinstance(type_, m.ArrayKind) and \
                    isinstance(type_.T, m.BitKind):
                width_str = f"[{len(type_) - 1}:0] "
            if type_.isoutput():
                t = "wire"
            elif type_.isinput():
                t = "reg"
            else:
                raise NotImplementedError()
            return f"    {t} {width_str}{name};\n", [f".{name}({name})"]

    def generate_code(self, actions):
        initial_body = ""
        declarations = ""
        port_list = []
        for name, type_ in self.circuit.IO.ports.items():
            result = SystemVerilogTarget.generate_port_code(name, type_)
            declarations += result[0]
            port_list.extend(result[1])

        for i, action in enumerate(actions):
            code = self.generate_action_code(i, action)
            for line in code:
                initial_body += f"        {line}\n"

        src = src_tpl.format(
            declarations=declarations,
            initial_body=initial_body,
            port_list=",\n        ".join(port_list),
            circuit_name=self.circuit_name,
        )

        return src

    def run(self, actions):
        test_bench_file = self.directory / Path(f"{self.circuit_name}_tb.sv")
        # Write the verilator driver to file.
        src = self.generate_code(actions)
        with open(test_bench_file, "w") as f:
            print(src)
            f.write(src)
        cmd_file = self.directory / Path(f"{self.circuit_name}_cmd.tcl")
        if self.simulator == "ncsim":
            with open(cmd_file, "w") as f:
                f.write(ncsim_cmd_string)
            cmd = f"""\
irun -top {self.circuit_name}_tb -timescale {self.timescale} -access +rwc -notimingchecks -input {cmd_file} {test_bench_file} {self.verilog_file}
"""  # nopep8
        else:
            cmd = f"""\
vcs -sverilog -full64 +v2k -timescale={self.timescale} -LDFLAGS -Wl,--no-as-needed  {test_bench_file} {self.verilog_file}
"""  # nopep8

        print(f"Running command: {cmd}")
        assert not subprocess.call(cmd, cwd=self.directory, shell=True)
        if self.simulator == "vcs":
            print(f"Running command: {cmd}")
            assert not subprocess.call("./simv", cwd=self.directory, shell=True)
