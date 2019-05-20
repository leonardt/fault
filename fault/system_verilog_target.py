from fault.verilog_target import VerilogTarget, verilog_name
import magma as m
from pathlib import Path
import fault.actions as actions
from hwtypes import BitVector
import fault.value_utils as value_utils
from fault.select_path import SelectPath
import subprocess
from fault.wrapper import PortWrapper
import fault


src_tpl = """\
module {circuit_name}_tb;
{declarations}

    {circuit_name} dut (
        {port_list}
    );

    initial begin
{initial_body}
        #20 $finish;
    end

endmodule
"""


class SystemVerilogTarget(VerilogTarget):
    def __init__(self, circuit, circuit_name=None, directory="build/",
                 skip_compile=False, magma_output="coreir-verilog",
                 magma_opts={}, include_verilog_libraries=[], simulator=None,
                 timescale="1ns/1ns", clock_step_delay=5, num_cycles=10000,
                 dump_vcd=True, no_warning=False):
        """
        circuit: a magma circuit

        circuit_name: the name of the circuit (default is circuit.name)

        directory: directory to use for generating collateral, buildling, and
                   running simulator

        skip_compile: (boolean) whether or not to compile the magma circuit

        magma_output: Set the output parameter to m.compile
                      (default coreir-verilog)

        magma_opts: Options dictionary for `magma.compile` command

        simulator: "ncsim", "vcs", or "iverilog"

        timescale: Set the timescale for the verilog simulation
                   (default 1ns/1ns)

        clock_step_delay: Set the number of steps to delay for each step of the
                          clock
        """
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         include_verilog_libraries, magma_output, magma_opts)
        if simulator is None:
            raise ValueError("Must specify simulator when using system-verilog"
                             " target")
        if simulator not in {"vcs", "ncsim", "iverilog"}:
            raise ValueError(f"Unsupported simulator {simulator}")
        self.simulator = simulator
        self.timescale = timescale
        self.clock_step_delay = clock_step_delay
        self.num_cycles = num_cycles
        self.dump_vcd = dump_vcd
        self.no_warning = no_warning
        self.declarations = []

    def make_name(self, port):
        if isinstance(port, SelectPath):
            if len(port) > 2:
                name = f"dut.{port.system_verilog_path}"
            else:
                # Top level ports assign to the external reg
                name = verilog_name(port[-1].name)
        elif isinstance(port, fault.WrappedVerilogInternalPort):
            name = f"dut.{port.path}"
        else:
            name = verilog_name(port.name)
        return name

    def process_value(self, port, value):
        if isinstance(port, m.SIntType) and value < 0:
            # Handle sign extension for verilator since it expects and
            # unsigned c type
            port_len = len(port)
            value = BitVector(value, port_len).as_uint()
        elif value is fault.UnknownValue:
            value = "'X"
        elif isinstance(value, actions.Peek):
            if isinstance(value.port, fault.WrappedVerilogInternalPort):
                value = f"dut.{value.port.path}"
            else:
                value = f"{value.port.name}"
        elif isinstance(value, PortWrapper):
            value = f"dut.{value.select_path.system_verilog_path}"
        elif isinstance(value, actions.FileRead):
            new_value = f"{value.file.name_without_ext}_in"
            if value.file.chunk_size == 1:
                # Assume that the user didn't want an array 1 byte, so unpack
                new_value += "[0]"
            value = new_value
        return value

    def make_poke(self, i, action):
        name = self.make_name(action.port)
        # For now we assume that verilog can handle big ints
        value = self.process_value(action.port, action.value)
        return [f"{name} = {value};", f"#{self.clock_step_delay}"]

    def make_print(self, i, action):
        ports = ", ".join(f"{self.make_name(port)}" for port in action.ports)
        if ports:
            ports = ", " + ports
        return [f'$write("{action.format_str}"{ports});']

    def make_loop(self, i, action):
        self.declarations.append(f"integer {action.loop_var};")
        code = []
        code.append(f"for ({action.loop_var} = 0;"
                    f" {action.loop_var} < {action.n_iter};"
                    f" {action.loop_var}++) begin")

        for inner_action in action.actions:
            # TODO: Handle relative offset of sub-actions
            inner_code = self.generate_action_code(i, inner_action)
            code += ["    " + x for x in inner_code]

        code.append("end")
        return code

    def make_file_open(self, i, action):
        if action.file.mode not in {"r", "w"}:
            raise NotImplementedError(action.file.mode)
        name = action.file.name_without_ext
        self.declarations.append(
            f"reg [7:0] {name}_in[0:{action.file.chunk_size - 1}];")
        self.declarations.append(f"integer {name}_file;")
        code = f"""\
{name}_file = $fopen(\"{action.file.name}\", \"{action.file.mode}\");
if (!{name}_file) $error("Could not open file {action.file.name}: %0d", {name}_file);
"""  # noqa
        return code.splitlines()

    def make_file_close(self, i, action):
        return [f"$fclose({action.file.name_without_ext}_file);"]

    def make_file_read(self, i, action):
        decl = f"integer __i;"
        if decl not in self.declarations:
            self.declarations.append(decl)
        code = f"""\
for (__i = 0; __i < {action.file.chunk_size}; __i++) begin
    {action.file.name_without_ext}_in[__i] = $fgetc({action.file.name_without_ext}_file);
end
"""  # noqa
        return code.splitlines()

    def make_file_write(self, i, action):
        value = self.make_name(action.value)
        return [f"$fwrite({action.file.name_without_ext}_file, \"%c\", "
                f"{value});"]

    def make_expect(self, i, action):
        if value_utils.is_any(action.value):
            return []
        name = self.make_name(action.port)
        if isinstance(action.port, SelectPath):
            debug_name = action.port[-1].name
        elif isinstance(action.port, fault.WrappedVerilogInternalPort):
            debug_name = name
        else:
            debug_name = action.port.name
        value = self.process_value(action.port, action.value)

        return f"""
if ({name} != {value}) begin
    $error(\"Failed on action={i} checking port {debug_name}. Expected %x, got %x\" , {value}, {name});
end;
""".splitlines()  # noqa

    def make_eval(self, i, action):
        # Eval implicit in SV simulations
        return []

    def make_step(self, i, action):
        name = verilog_name(action.clock.name)
        code = []
        for step in range(action.steps):
            code.append(f"#5 {name} ^= 1;")
        return code

    def generate_recursive_port_code(self, name, type_):
        port_list = []
        if isinstance(type_, m.ArrayKind):
            for j in range(type_.N):
                result = self.generate_port_code(
                    name + "_" + str(j), type_.T
                )
                port_list.extend(result)
        elif isinstance(type_, m.TupleKind):
            for k, t in zip(type_.Ks, type_.Ts):
                result = self.generate_port_code(
                    name + "_" + str(k), t
                )
                port_list.extend(result)
        return port_list

    def generate_port_code(self, name, type_):
        is_array_of_bits = isinstance(type_, m.ArrayKind) and \
            not isinstance(type_.T, m.BitKind)
        if is_array_of_bits or isinstance(type_, m.TupleKind):
            return self.generate_recursive_port_code(name, type_)
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
            self.declarations.append(f"    {t} {width_str}{name};\n")
            return [f".{name}({name})"]

    def generate_code(self, actions):
        initial_body = ""
        port_list = []
        for name, type_ in self.circuit.IO.ports.items():
            result = self.generate_port_code(name, type_)
            port_list.extend(result)

        for i, action in enumerate(actions):
            code = self.generate_action_code(i, action)
            for line in code:
                initial_body += f"        {line}\n"

        src = src_tpl.format(
            declarations="\n".join(self.declarations),
            initial_body=initial_body,
            port_list=",\n        ".join(port_list),
            circuit_name=self.circuit_name,
        )

        return src

    def run(self, actions):
        test_bench_file = Path(f"{self.circuit_name}_tb.sv")

        # Write the verilator driver to file.
        src = self.generate_code(actions)
        with open(self.directory / test_bench_file, "w") as f:
            f.write(src)
        verilog_libraries = " ".join(str(x) for x in
                                     self.include_verilog_libraries)
        cmd_file = Path(f"{self.circuit_name}_cmd.tcl")
        if self.simulator == "ncsim":
            if self.dump_vcd:
                vcd_command = """
database -open -vcd vcddb -into verilog.vcd -default -timescale ps
probe -create -all -vcd -depth all"""
            else:
                vcd_command = ""
            ncsim_cmd_string = f"""\
{vcd_command}
run {self.num_cycles}ns
quit"""
            if self.no_warning:
                warning = "-neverwarn"
            else:
                warning = ""
            with open(self.directory / cmd_file, "w") as f:
                f.write(ncsim_cmd_string)
            cmd = f"""\
irun -top {self.circuit_name}_tb -timescale {self.timescale} -access +rwc -notimingchecks {warning} -input {cmd_file} {test_bench_file} {self.verilog_file} {verilog_libraries}
"""  # nopep8
        elif self.simulator == "vcs":
            cmd = f"""\
vcs -sverilog -full64 +v2k -timescale={self.timescale} -LDFLAGS -Wl,--no-as-needed  {test_bench_file} {self.verilog_file} {verilog_libraries}
"""  # nopep8
        elif self.simulator == "iverilog":
            cmd = f"iverilog -o {self.circuit_name}_tb {test_bench_file} {self.verilog_file}"  # noqa
        else:
            raise NotImplementedError(self.simulator)

        print(f"Running command: {cmd}")
        assert not subprocess.call(cmd, cwd=self.directory, shell=True)
        if self.simulator == "vcs":
            result = subprocess.run("./simv", cwd=self.directory, shell=True,
                                    capture_output=True)
        elif self.simulator == "iverilog":
            result = subprocess.run(f"vvp -N {self.circuit_name}_tb",
                                    cwd=self.directory, shell=True,
                                    capture_output=True)
        if self.simulator in {"vcs", "iverilog"}:
            # VCS and iverilog do not set the return code when a
            # simulation exits with an error, so we check the result
            # of stdout to see if "Error" is present
            print(result.stdout.decode())
            assert not result.returncode, \
                f"Running {self.simulator} binary failed"
            assert "Error" not in str(result.stdout), \
                f"\"Error\" found in stdout of {self.simulator} run"
