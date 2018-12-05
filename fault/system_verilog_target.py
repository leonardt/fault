from fault.verilog_target import VerilogTarget
import magma as m
from pathlib import Path
import fault.actions as actions
import fault.verilator_utils as verilator_utils
from bit_vector import BitVector
import fault.value_utils as value_utils
import subprocess
from fault.util import flatten


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
                 skip_compile=False, magma_output="verilog"):
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         magma_output)

    @staticmethod
    def generate_array_action_code(i, action):
        result = []
        for j in range(action.port.N):
            if isinstance(action, actions.Print):
                value = action.format_str
            else:
                value = action.value[j]
            result += [
                SystemVerilogTarget.generate_action_code(
                    i, type(action)(action.port[j], value)
                )]
        return flatten(result)

    @staticmethod
    def generate_action_code(i, action):
        if isinstance(action, actions.Poke):
            if isinstance(action.port, m.ArrayType) and \
                    not isinstance(action.port.T, m.BitKind):
                return SystemVerilogTarget.generate_array_action_code(i, action)
            name = verilator_utils.verilator_name(action.port.name)
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
                return [f"{name} = {value};", "#5"]
        if isinstance(action, actions.Print):
            name = verilator_utils.verilator_name(action.port.name)
            if isinstance(action.port, m.ArrayType) and \
                    not isinstance(action.port.T, m.BitKind):
                return SystemVerilogTarget.generate_array_action_code(i, action)
            else:
                return [f'$display("{action.port.debug_name} = '
                        f'{action.format_str}", {name});']
        if isinstance(action, actions.Expect):
            # For verilator, if an expect is "AnyValue" we don't need to
            # perform the expect.
            if value_utils.is_any(action.value):
                return []
            if isinstance(action.port, m.ArrayType) and \
                    not isinstance(action.port.T, m.BitKind):
                return SystemVerilogTarget.generate_array_action_code(i, action)
            name = verilator_utils.verilator_name(action.port.name)
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
        if isinstance(action, actions.Eval):
            # Eval implicit in SV simulations
            return []
        if isinstance(action, actions.Step):
            name = verilator_utils.verilator_name(action.clock.name)
            code = []
            for step in range(action.steps):
                # code.append("top->eval();")
                # code.append("main_time++;")
                # code.append("#if VM_TRACE")
                # code.append("tracer->dump(main_time);")
                # code.append("#endif")
                code.append(f"#5 {name} ^= 1;")
            return code
        raise NotImplementedError(action)

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
            print(type_)
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
            code = SystemVerilogTarget.generate_action_code(i, action)
            for line in code:
                initial_body += f"        {line}\n"

        src = src_tpl.format(
            declarations=declarations,
            initial_body=initial_body,
            port_list=",\n        ".join(port_list),
            circuit_name=self.circuit_name,
        )

        return src

    def run(self, actions, timescale="1ns/1ns", simulator="ncsim"):
        """
        Supported simulators: "ncsim", "vcs"
        """
        test_bench_file = self.directory / Path(f"{self.circuit_name}_tb.sv")
        # Write the verilator driver to file.
        src = self.generate_code(actions)
        with open(test_bench_file, "w") as f:
            print(src)
            f.write(src)
        cmd_file = self.directory / Path(f"{self.circuit_name}_cmd.tcl")
        if simulator == "ncsim":
            with open(cmd_file, "w") as f:
                f.write(ncsim_cmd_string)
            cmd = f"""\
irun -top {self.circuit_name}_tb -timescale {timescale} -access +rwc -notimingchecks -input {cmd_file} {test_bench_file} {self.verilog_file}
"""  # nopep8
        else:
            cmd = f"""\
vcs -sverilog -full64 +v2k -timescale={timescale} -LDFLAGS -Wl,--no-as-needed  {test_bench_file} {self.verilog_file}
"""  # nopep8

        print(f"Running command: {cmd}")
        assert not subprocess.call(cmd, cwd=self.directory, shell=True)
        if simulator == "vcs":
            print(f"Running command: {cmd}")
            assert not subprocess.call("./simv", cwd=self.directory, shell=True)
