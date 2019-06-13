import logging
from fault.verilog_target import VerilogTarget, verilog_name
import magma as m
from pathlib import Path
import fault.actions as actions
from hwtypes import BitVector, AbstractBitVectorMeta
import fault.value_utils as value_utils
from fault.select_path import SelectPath
import subprocess
from fault.wrapper import PortWrapper
import fault
import fault.expression as expression
import os


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

    def process_peek(self, value):
        if isinstance(value.port, fault.WrappedVerilogInternalPort):
            return f"dut.{value.port.path}"
        else:
            return f"{value.port.name}"

    def make_var(self, i, action):
        if isinstance(action._type, AbstractBitVectorMeta):
            self.declarations.append(
                f"reg [{action._type.size - 1}:0] {action.name};")
            return []
        raise NotImplementedError(action._type)

    def make_file_scan_format(self, i, action):
        var_args = ", ".join(f"{var.name}" for var in action.args)
        return [f"$fscanf({action.file.name_without_ext}_file, "
                f"\"{action._format}\", {var_args});"]

    def process_value(self, port, value):
        if isinstance(value, BitVector):
            value = f"{len(value)}'d{value.as_uint()}"
        elif isinstance(port, m.SIntType) and value < 0:
            port_len = len(port)
            value = BitVector[port_len](value).as_uint()
            value = f"{port_len}'d{value}"
        elif value is fault.UnknownValue:
            value = "'X"
        elif isinstance(value, actions.Peek):
            value = self.process_peek(value)
        elif isinstance(value, PortWrapper):
            value = f"dut.{value.select_path.system_verilog_path}"
        elif isinstance(value, actions.FileRead):
            new_value = f"{value.file.name_without_ext}_in"
            value = new_value
        elif isinstance(value, expression.Expression):
            value = f"({self.compile_expression(value)})"
        return value

    def compile_expression(self, value):
        if isinstance(value, expression.BinaryOp):
            left = self.compile_expression(value.left)
            right = self.compile_expression(value.right)
            op = value.op_str
            return f"{left} {op} {right}"
        elif isinstance(value, PortWrapper):
            return f"dut.{value.select_path.system_verilog_path}"
        elif isinstance(value, actions.Peek):
            return self.process_peek(value)
        elif isinstance(value, actions.Var):
            value = value.name
        return value

    def make_poke(self, i, action):
        name = self.make_name(action.port)
        # For now we assume that verilog can handle big ints
        value = self.process_value(action.port, action.value)
        return [f"{name} = {value};", f"#{self.clock_step_delay};"]

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
        bit_size = action.file.chunk_size * 8 - 1
        self.declarations.append(
            f"reg [{bit_size}:0] {name}_in;")
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
        if action.file.endianness == "big":
            loop_expr = f"__i = {action.file.chunk_size - 1}; __i >= 0; __i--"
        else:
            loop_expr = f"__i = 0; __i < {action.file.chunk_size}; __i++"
        code = f"""\
{action.file.name_without_ext}_in = 0;
for ({loop_expr}) begin
    {action.file.name_without_ext}_in |= $fgetc({action.file.name_without_ext}_file) << (8 * __i);
end
"""  # noqa
        return code.splitlines()

    def make_file_write(self, i, action):
        value = self.make_name(action.value)
        mask_size = action.file.chunk_size * 8
        decl = f"integer __i;"
        if decl not in self.declarations:
            self.declarations.append(decl)
        if action.file.endianness == "big":
            loop_expr = f"__i = {action.file.chunk_size - 1}; __i >= 0; __i--"
        else:
            loop_expr = f"__i = 0; __i < {action.file.chunk_size}; __i++"
        code = f"""\
for ({loop_expr}) begin
    $fwrite({action.file.name_without_ext}_file, \"%c\", ({value} >> (8 * __i)) & {mask_size}'hFF);
end
"""  # noqa
        return code.splitlines()

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

    def make_while(self, i, action):
        code = []
        cond = self.compile_expression(action.loop_cond)

        code.append(f"while ({cond}) begin")

        for inner_action in action.actions:
            # TODO: Handle relative offset of sub-actions
            inner_code = self.generate_action_code(i, inner_action)
            code += ["    " + x for x in inner_code]

        code.append("end")

        return code

    def make_if(self, i, action):
        code = []
        cond = self.compile_expression(action.cond)

        code.append(f"if ({cond}) begin")

        for inner_action in action.actions:
            # TODO: Handle relative offset of sub-actions
            inner_code = self.generate_action_code(i, inner_action)
            code += ["    " + x for x in inner_code]

        code.append("end")

        if action.else_actions:
            code[-1] += " else begin"
            for inner_action in action.else_actions:
                # TODO: Handle relative offset of sub-actions
                inner_code = self.generate_action_code(i, inner_action)
                code += ["    " + x for x in inner_code]

            code.append("end")

        return code

    def generate_recursive_port_code(self, name, type_, power_args):
        port_list = []
        if isinstance(type_, m.ArrayKind):
            for j in range(type_.N):
                result = self.generate_port_code(
                    name + "_" + str(j), type_.T, power_args
                )
                port_list.extend(result)
        elif isinstance(type_, m.TupleKind):
            for k, t in zip(type_.Ks, type_.Ts):
                result = self.generate_port_code(
                    name + "_" + str(k), t, power_args
                )
                port_list.extend(result)
        return port_list

    def generate_port_code(self, name, type_, power_args):
        is_array_of_bits = isinstance(type_, m.ArrayKind) and \
            not isinstance(type_.T, m.BitKind)
        if is_array_of_bits or isinstance(type_, m.TupleKind):
            return self.generate_recursive_port_code(name, type_, power_args)
        else:
            width_str = ""
            if isinstance(type_, m.ArrayKind) and \
                    isinstance(type_.T, m.BitKind):
                width_str = f"[{len(type_) - 1}:0] "
            if name in power_args.get("supply0s", []):
                t = "supply0"
            elif name in power_args.get("supply1s", []):
                t = "supply1"
            elif name in power_args.get("tris", []):
                t = "tri"
            elif type_.isoutput():
                t = "wire"
            elif type_.isinput():
                t = "reg"
            else:
                raise NotImplementedError()
            self.declarations.append(f"    {t} {width_str}{name};\n")
            return [f".{name}({name})"]

    def generate_code(self, actions, power_args):
        initial_body = ""
        port_list = []
        for name, type_ in self.circuit.IO.ports.items():
            result = self.generate_port_code(name, type_, power_args)
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

    def run(self, actions, power_args={}):
        test_bench_file = Path(f"{self.circuit_name}_tb.sv")

        # Write the verilator driver to file.
        src = self.generate_code(actions, power_args)
        tb_file = self.directory / test_bench_file
        # If there's an old test bench file, ncsim might not recompile based on
        # the timestamp (1s granularity), see
        # https://github.com/StanfordAHA/lassen/issues/111
        # so we check if the new/old file have the same timestamp and edit them
        # to force an ncsim recompile
        check_timestamp = os.path.isfile(tb_file)
        if check_timestamp:
            check_timestamp = True
            old_stat_result = os.stat(tb_file)
            old_times = (old_stat_result.st_atime, old_stat_result.st_mtime)
        with open(tb_file, "w") as f:
            f.write(src)
        if check_timestamp:
            new_stat_result = os.stat(tb_file)
            new_times = (new_stat_result.st_atime, new_stat_result.st_mtime)
            if old_times[0] <= new_times[0] or new_times[1] <= old_times[1]:
                new_times = (old_times[0] + 1, old_times[1] + 1)
                os.utime(tb_file, times=new_times)
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

        logging.debug(f"Running command: {cmd}")
        result = subprocess.run(cmd, cwd=self.directory, shell=True,
                                capture_output=True)
        logging.info(result.stdout.decode())
        assert not result.returncode, "Error running system verilog simulator"
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
            logging.info(result.stdout.decode())
            assert not result.returncode, \
                f"Running {self.simulator} binary failed"
            if self.simulator == "vcs":
                error_str = "Error"
            elif self.simulator == "iverilog":
                error_str = "ERROR"
            assert error_str not in str(result.stdout), \
                f"\"{error_str}\" found in stdout of {self.simulator} run"
