from fault.verilog_target import VerilogTarget
import magma as m
from pathlib import Path
import fault.actions as actions
import fault.verilator_utils as verilator_utils
from bit_vector import BitVector
import fault.value_utils as value_utils
import subprocess


src_tpl = """\
`timescale 1ns/1ns

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


class SystemVerilogTarget(VerilogTarget):
    def __init__(self, circuit, circuit_name=None, directory="build/",
                 skip_compile=False, magma_output="verilog"):
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         magma_output)

    @staticmethod
    def generate_action_code(i, action):
        if isinstance(action, actions.Poke):
            if isinstance(action.port, m.ArrayType) and \
                    not isinstance(action.port.T, m.BitKind):
                return VerilatorTarget.generate_array_action_code(i, action)
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
                return [f"{name} = {value};", "#1"]
        if isinstance(action, actions.Print):
            name = verilator_utils.verilator_name(action.port.name)
            if isinstance(action.port, m.ArrayType) and \
                    not isinstance(action.port.T, m.BitKind):
                return VerilatorTarget.generate_array_action_code(i, action)
            else:
                return [f'$display("{action.port.debug_name} = '
                        f'{action.format_str}\\n", {name});']
        if isinstance(action, actions.Expect):
            # For verilator, if an expect is "AnyValue" we don't need to
            # perform the expect.
            if value_utils.is_any(action.value):
                return []
            if isinstance(action.port, m.ArrayType) and \
                    not isinstance(action.port.T, m.BitKind):
                return VerilatorTarget.generate_array_action_code(i, action)
            name = verilator_utils.verilator_name(action.port.name)
            value = action.value
            if isinstance(value, actions.Peek):
                value = f"{value.port.name}"
            elif isinstance(action.port, m.SIntType) and value < 0:
                # Handle sign extension for verilator since it expects and
                # unsigned c type
                port_len = len(action.port)
                value = BitVector(value, port_len).as_uint()

            return [f"if ({name} != {value}) $error(\"Failed on iteration={i} checking port {action.port.name}\");"]
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

    def generate_code(self, actions):
        initial_body = ""
        port_list = []
        declarations = ""
        for name, value in self.circuit.IO.ports.items():
            width_str = ""
            if isinstance(value, m.ArrayType) and isinstance(value.T, m.BitKind):
                width_str = f"[{len(value) - 1}:0] "
            if value.isoutput():
                t = "wire"
            elif value.isinput():
                t = "reg"
            else:
                raise NotImplementedError()
            declarations += f"    {t} {width_str}{name};\n"
            port_list.append(f".{name}({name})")

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

    def run(self, actions):
        test_bench_file = self.directory / Path(f"{self.circuit_name}_tb.sv")
        # Write the verilator driver to file.
        src = self.generate_code(actions)
        with open(test_bench_file, "w") as f:
            print(src)
            f.write(src)
        cmd_file = self.directory / Path(f"{self.circuit_name}_cmd.tcl")
        with open(cmd_file, "w") as f:
            f.write("""\
database -open -vcd vcddb -into verilog.vcd -default -timescale ps
probe -create -all -vcd -depth all
run 10000ns
quit
""")
        cmd = f"""\
irun -top {self.circuit_name}_tb -timescale 1ns/1ps -access +rwc -notimingchecks -input {cmd_file} {test_bench_file} {self.verilog_file}
"""  # nopep8
        print(f"Running command: {cmd}")
        assert not subprocess.call(cmd, cwd=self.directory, shell=True)
