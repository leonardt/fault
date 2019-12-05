import fault
from pathlib import Path
import magma as m
import fault.actions as actions
from fault.actions import Poke, Eval
from fault.verilog_target import VerilogTarget
from fault.verilog_utils import verilator_name
import fault.value_utils as value_utils
from fault.verilator_utils import (verilator_make_cmd, verilator_comp_cmd,
                                   verilator_version)
from fault.select_path import SelectPath
from fault.wrapper import PortWrapper, InstanceWrapper
import math
from hwtypes import BitVector, AbstractBitVectorMeta
from fault.random import constrained_random_bv
from fault.subprocess_run import subprocess_run
import fault.utils as utils
import fault.expression as expression
import platform


max_bits = 64 if platform.architecture()[0] == "64bit" else 32


src_tpl = """\
{includes}

// Based on https://www.veripool.org/projects/verilator/wiki/Manual-verilator#CONNECTING-TO-C
vluint64_t main_time = 0;       // Current simulation time
// This is a 64-bit integer to reduce wrap over issues and
// allow modulus.  You can also use a double, if you wish.

double sc_time_stamp () {{       // Called by $time in Verilog
    return main_time;           // converts to double, to match
                                // what SystemC does
}}

#if VM_TRACE
VerilatedVcdC* tracer;
#endif

void my_assert(
    unsigned int got,
    unsigned int expected,
    int i,
    const char* port) {{
  if (got != expected) {{
    std::cerr << std::endl;  // end the current line
    std::cerr << \"Got      : 0x\" << std::hex << got << std::endl;
    std::cerr << \"Expected : 0x\" << std::hex << expected << std::endl;
    std::cerr << \"i        : \" << std::dec << i << std::endl;
    std::cerr << \"Port     : \" << port << std::endl;
#if VM_TRACE
    // Dump one more timestep so we see the current values
    main_time++;
    tracer->dump(main_time);
    tracer->close();
#endif
    exit(1);
  }}
}}

int main(int argc, char **argv) {{
  Verilated::commandArgs(argc, argv);
  V{circuit_name}* top = new V{circuit_name};

#if VM_TRACE
  Verilated::traceEverOn(true);
  tracer = new VerilatedVcdC;
  top->trace(tracer, 99);
  mkdir("logs", S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
  tracer->open("logs/{circuit_name}.vcd");
#endif

{main_body}

#if VM_TRACE
  tracer->close();
#endif
}}
"""  # nopep8


class VerilatorTarget(VerilogTarget):
    def __init__(self, circuit, directory="build/",
                 flags=None, skip_compile=False, include_verilog_libraries=None,
                 include_directories=None, magma_output="coreir-verilog",
                 circuit_name=None, magma_opts=None, skip_verilator=False,
                 disp_type='on_error'):
        """
        Params:
            `include_verilog_libraries`: a list of verilog libraries to include
            with the -v flag.  From the verilator docs:
                -v <filename>              Verilog library

            `include_directories`: a list of directories to include using the
            -I flag. From the the verilator docs:
                -I<dir>                    Directory to search for includes
        """
        # Set defaults
        if include_verilog_libraries is None:
            include_verilog_libraries = []
        if magma_opts is None:
            magma_opts = {}

        # Save settings
        self.disp_type = disp_type

        # Call super constructor
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         include_verilog_libraries, magma_output, magma_opts)

        # Compile the design using `verilator`, if not skip
        if not skip_verilator:
            driver_file = self.directory / Path(
                f"{self.circuit_name}_driver.cpp")
            comp_cmd = verilator_comp_cmd(
                top=self.circuit_name,
                verilog_filename=self.verilog_file.name,
                include_verilog_libraries=self.include_verilog_libraries,
                include_directories=include_directories,
                driver_filename=driver_file.name,
                verilator_flags=flags
            )
            # shell=True since 'verilator' is actually a shell script
            subprocess_run(comp_cmd, cwd=self.directory, shell=True,
                           disp_type=self.disp_type)

        # Initialize variables
        self.debug_includes = set()
        self.verilator_version = verilator_version(disp_type=self.disp_type)

    def get_verilator_prefix(self):
        if self.verilator_version > 3.874:
            return f"{self.circuit_name}"
        else:
            return f"v"

    def process_peek(self, value):
        if isinstance(value.port, fault.WrappedVerilogInternalPort):
            path = value.port.path.replace(".", "->")
            return f"top->{self.get_verilator_prefix()}->{path}"
        else:
            return f"top->{verilator_name(value.port.name)}"

    def process_value(self, port, value):
        if isinstance(value, expression.Expression):
            return self.compile_expression(value)
        elif isinstance(value, (int, BitVector)) and value < 0:
            return self.process_signed_values(port, value)
        elif isinstance(value, (int, BitVector)):
            return value
        elif isinstance(value, actions.Var):
            return value.name
        return value

    def process_signed_values(self, port, value):
        # Handle sign extension for verilator since it expects and unsigned
        # c type
        if isinstance(port, SelectPath):
            port = port[-1]
        port_len = len(port)
        return BitVector[port_len](value).as_uint()

    def compile_expression(self, value):
        if isinstance(value, expression.BinaryOp):
            left = self.compile_expression(value.left)
            right = self.compile_expression(value.right)
            if isinstance(value, expression.Pow):
                raise NotImplementedError("C does not have a pow operator")
            else:
                op = value.op_str
            return f"({left} {op} {right})"
        elif isinstance(value, PortWrapper):
            return f"top->{value.select_path.verilator_path}"
        elif isinstance(value, actions.Peek):
            return self.process_peek(value)
        elif isinstance(value, actions.Var):
            return value.name
        return value

    def make_poke(self, i, action):
        if self.verilator_version > 3.874:
            prefix = f"{self.circuit_name}"
        else:
            prefix = f"v"
        if isinstance(action.port, fault.WrappedVerilogInternalPort):
            path = action.port.path.replace(".", "->")
            name = f"{prefix}->{path}"
        elif isinstance(action.port, SelectPath):
            name = ""
            if len(action.port) > 2:
                # TODO: Find the version that they changed this, 3.874 is known
                # to use top->v instead of top->{circuit_name}
                name += f"{prefix}->"
            name += action.port.verilator_path
            if len(action.port) > 2:
                self.debug_includes.add(f"{action.port[0].circuit.name}")
            for item in action.port[1:-1]:
                circuit = type(item.instance)
                circuit_name = circuit.verilog_name
                # Verilator specializes each parametrization into a separate
                # mdoule, this is an attempt to reverse engineer the naming
                # scheme
                if circuit_name == "coreir_reg":
                    circuit_name += "_"
                    circuit_name += f"_I{circuit.coreir_configargs['init']}"
                    circuit_name += f"_W{circuit.coreir_genargs['width']}"
                elif circuit_name == "coreir_reg_arst":
                    circuit_name += "_"
                    circuit_name += f"_I{circuit.coreir_configargs['init']}"
                    if circuit.coreir_genargs['width'] != 1:
                        circuit_name += f"_W{circuit.coreir_genargs['width']}"
                self.debug_includes.add(f"{circuit_name}")
        else:
            name = verilator_name(action.port.name)

        # Special case poking internal registers
        is_reg_poke = isinstance(action.port, SelectPath) and \
            isinstance(action.port[-1], fault.WrappedVerilogInternalPort) \
            and action.port[-1].path == "outReg"

        if isinstance(action.value, BitVector) and \
                action.value.num_bits > max_bits:
            pokes = []
            # For some reason, verilator chunks it by 32 instead of max_bits
            slice_range = 32
            for i in range(math.ceil(action.value.num_bits / slice_range)):
                value = action.value[i * slice_range:min(
                    (i + 1) * slice_range, action.value.num_bits)]
                pokes += [f"top->{name}[{i}] = {value};"]
            if is_reg_poke:
                raise NotImplementedError()
            return pokes
        else:
            value = action.value
            if isinstance(value, actions.FileRead):
                mask = "FF" * value.file.chunk_size
                value = " | ".join(f"{value.file.name_without_ext}_in[{i}]" for
                                   i in range(value.file.chunk_size))
                value = f"({value}) & 0x{mask}"
            value = self.process_value(action.port, value)
            result = [f"top->{name} = {value};"]
            # Hack to support verilator's semantics, need to set the register
            # mux values for expected behavior
            if is_reg_poke:
                action.port[-1].path = "out"
                result += self.make_poke(i, action)
                action.port[-1].path = "in"
                result += self.make_poke(i, action)
                if "enable_mux" in action.port[-3].instance_map:
                    mux_inst = action.port[-3].instance_map["enable_mux"]
                    action.port[-2] = InstanceWrapper(mux_inst, action.port[-3])
                    action.port[-1] = type(mux_inst).I0
                    result += self.make_poke(i, action)
            return result

    def make_print(self, i, action):
        port_names = []
        prefix = self.get_verilator_prefix()
        for port in action.ports:
            if isinstance(port, fault.WrappedVerilogInternalPort):
                path = port.path.replace(".", "->")
                name = f"{prefix}->{path}"
            elif isinstance(port, PortWrapper):
                port = port.select_path
                name = port.verilator_path
                if len(port) > 2:
                    name = f"{prefix}->" + name
                if self.verilator_version >= 3.856:
                    if len(port) > 2:
                        self.debug_includes.add(f"{port[0].circuit.name}")
                for item in port[1:-1]:
                    circuit_name = type(item.instance).name
                    self.debug_includes.add(f"{circuit_name}")
            else:
                name = verilator_name(port.name)
            port_names.append(name)
        ports = ", ".join(f"top->{name}" for name in port_names)
        if ports:
            ports = ", " + ports
        return [f'printf("{action.format_str}"{ports});']

    def make_read(self, i, action):
        msg = 'read not implemented for Verilator target'
        raise NotImplementedError(msg)

    def make_expect(self, i, action):
        # For verilator, if an expect is "AnyValue" we don't need to
        # perform the expect.
        if value_utils.is_any(action.value):
            return []
        prefix = self.get_verilator_prefix()
        if isinstance(action.port, fault.WrappedVerilogInternalPort):
            path = action.port.path.replace(".", "->")
            name = f"{prefix}->{path}"
            debug_name = name
        elif isinstance(action.port, SelectPath):
            name = action.port.verilator_path
            if len(action.port) > 2:
                name = f"{prefix}->" + name
            if self.verilator_version >= 3.856:
                if len(action.port) > 2:
                    self.debug_includes.add(f"{action.port[0].circuit.name}")
            for item in action.port[1:-1]:
                circuit_name = type(item.instance).name
                self.debug_includes.add(f"{circuit_name}")
            debug_name = action.port[-1].debug_name
        else:
            name = verilator_name(action.port.name)
            debug_name = action.port.debug_name
        value = action.value
        if isinstance(value, actions.Peek):
            value = self.process_peek(value)
        elif isinstance(value, PortWrapper):
            if self.verilator_version >= 3.856:
                if len(action.port) > 2:
                    self.debug_includes.add(f"{action.port[0].circuit.name}")
            for item in value.select_path[1:-1]:
                circuit_name = type(item.instance).name
                self.debug_includes.add(f"{circuit_name}")
            value = f"top->{prefix}->" + value.select_path.verilator_path
        if isinstance(action.value, BitVector) and \
                action.value.num_bits > max_bits:
            asserts = []
            # For some reason, verilator chunks it by 32 instead of max_bits
            slice_range = 32
            for j in range(math.ceil(action.value.num_bits / slice_range)):
                value = action.value[j * slice_range:min(
                    (j + 1) * slice_range, action.value.num_bits)]
                asserts += [f"my_assert(top->{name}[{j}], {value}, "
                            f"{i}, \"{debug_name}\");"]
            return asserts
        else:
            value = self.process_value(action.port, value)
            port = action.port
            if isinstance(port, SelectPath):
                port = port[-1]
            elif isinstance(port, fault.WrappedVerilogInternalPort):
                port = port.type_
            if isinstance(port, m._BitType):
                port_len = 1
            else:
                port_len = len(port)
            mask = (1 << port_len) - 1

            return [f"my_assert(top->{name}, {value} & {mask}, "
                    f"{i}, \"{debug_name}\");"]

    def make_eval(self, i, action):
        return ["top->eval();", "main_time++;", "#if VM_TRACE",
                "tracer->dump(main_time);", "#endif"]

    def make_step(self, i, action):
        name = verilator_name(action.clock.name)
        code = []
        code.append("top->eval();")
        for step in range(action.steps):
            code.append(f"top->{name} ^= 1;")
            code.append("top->eval();")
            code.append("main_time++;")
            code.append("#if VM_TRACE")
            code.append("tracer->dump(main_time);")
            code.append("#endif")
        return code

    def make_loop(self, i, action):
        code = []
        code.append(f"for (int {action.loop_var} = 0;"
                    f" {action.loop_var} < {action.n_iter};"
                    f" {action.loop_var}++) {{")

        for inner_action in action.actions:
            # TODO: Handle relative offset of sub-actions
            inner_code = self.generate_action_code(i, inner_action)
            code += ["    " + x for x in inner_code]

        code.append("}")
        return code

    def make_file_open(self, i, action):
        name = action.file.name_without_ext
        code = f"""\
char {name}_in[{action.file.chunk_size}] = {{0}};
FILE *{name}_file = fopen("{action.file.name}", \"{action.file.mode}\");
if ({name}_file == NULL) {{
    std::cout << "Could not open file {action.file.name}" << std::endl;
    return 1;
}}"""
        return code.splitlines()

    def make_file_close(self, i, action):
        return [f"fclose({action.file.name_without_ext}_file);"]

    def make_file_write(self, i, action):
        value = f"top->{verilator_name(action.value.name)}"
        if action.file.endianness == "big":
            loop_expr = f"int i = {action.file.chunk_size - 1}; i >= 0; i--"
        else:
            loop_expr = f"int i = 0; i < {action.file.chunk_size}; i++"
        code = f"""\
for ({loop_expr}) {{
    int result = fputc(({value} >> (i * 8)) & 0xFF,
                       {action.file.name_without_ext}_file);
    if (result == EOF) {{
        std::cout << "Error writing to {action.file.name_without_ext}"
                  << std::endl;
        break;
    }}
}}
"""
        return code.splitlines()

    def make_file_read(self, i, action):
        if action.file.endianness == "big":
            loop_expr = f"int i = {action.file.chunk_size - 1}; i >= 0; i--"
        else:
            loop_expr = f"int i = 0; i < {action.file.chunk_size}; i++"
        code = f"""\
for ({loop_expr}) {{
    int result =  fgetc({action.file.name_without_ext}_file);
    if (result == EOF) {{
        std::cout << "Reached end of file {action.file.name_without_ext}"
                  << std::endl;
        break;
    }}
    {action.file.name_without_ext}_in[i] = result;
}}
"""
        return code.splitlines()

    def make_while(self, i, action):
        code = []
        cond = self.compile_expression(action.loop_cond)

        code.append(f"while ({cond}) {{")

        for inner_action in action.actions:
            # TODO: Handle relative offset of sub-actions
            inner_code = self.generate_action_code(i, inner_action)
            code += ["    " + x for x in inner_code]

        code.append("}")

        return code

    def make_if(self, i, action):
        code = []
        cond = self.compile_expression(action.cond)

        code.append(f"if ({cond}) {{")

        for inner_action in action.actions:
            # TODO: Handle relative offset of sub-actions
            inner_code = self.generate_action_code(i, inner_action)
            code += ["    " + x for x in inner_code]

        code.append("}")

        if action.else_actions:
            code[-1] += " else {"
            for inner_action in action.else_actions:
                # TODO: Handle relative offset of sub-actions
                inner_code = self.generate_action_code(i, inner_action)
                code += ["    " + x for x in inner_code]

            code.append("}")

        return code

    def make_var(self, i, action):
        if isinstance(action._type, AbstractBitVectorMeta) and \
                action._type.size == 32:
            return [f"unsigned int {action.name};"]
        raise NotImplementedError(action._type)

    def make_file_scan_format(self, i, action):
        var_args = ", ".join(f"&{var.name}" for var in action.args)
        return [f"fscanf({action.file.name_without_ext}_file, "
                f"\"{action._format}\", {var_args});"]

    def make_delay(self, i, action):
        # TODO: figure out how delay should be interpreted for VerilatorTarget
        raise NotImplementedError

    def generate_code(self, actions, verilator_includes, num_tests, circuit):
        if verilator_includes:
            # Include the top circuit by default
            verilator_includes.insert(
                0, f'{self.circuit_name}')
        includes = [
            f'"V{self.circuit_name}.h"',
        ] + [f'"V{self.circuit_name}_{include}.h"' for include in
             verilator_includes] + [
            '"verilated.h"',
            '<iostream>',
            '<fstream>',
            '<verilated_vcd_c.h>',
            '<sys/types.h>',
            '<sys/stat.h>',
        ]

        main_body = ""
        for i, action in enumerate(actions):
            code = self.generate_action_code(i, action)
            for line in code:
                main_body += f"  {line}\n"

        for i in range(num_tests):
            main_body += self.add_assumptions(circuit, actions, i)
            code = self.make_eval(i, Eval())
            for line in code:
                main_body += f"  {line}\n"
            main_body += self.add_guarantees(circuit, actions, i)

        includes += [f'"V{self.circuit_name}_{include}.h"' for include in
                     self.debug_includes]

        includes_src = "\n".join(["#include " + i for i in includes])
        src = src_tpl.format(
            includes=includes_src,
            main_body=main_body,
            circuit_name=self.circuit_name,
        )

        return src

    def run(self, actions, verilator_includes=None, num_tests=0,
            _circuit=None):
        # Set defaults
        if verilator_includes is None:
            verilator_includes = []

        # Write the verilator driver to file.
        src = self.generate_code(actions, verilator_includes, num_tests,
                                 _circuit)
        driver_file = self.directory / Path(f"{self.circuit_name}_driver.cpp")
        with open(driver_file, "w") as f:
            f.write(src)

        # Run makefile created by verilator
        make_cmd = verilator_make_cmd(self.circuit_name)
        subprocess_run(make_cmd, cwd=self.directory, disp_type=self.disp_type)

        # Run the executable created by verilator and write the standard
        # output to a logfile for later review or processing
        exe_cmd = [f'./obj_dir/V{self.circuit_name}']
        result = subprocess_run(exe_cmd, cwd=self.directory,
                                disp_type=self.disp_type)
        log = Path(self.directory) / 'obj_dir' / f'{self.circuit_name}.log'
        with open(log, 'w') as f:
            f.write(result.stdout)

    def add_assumptions(self, circuit, actions, i):
        main_body = ""
        for port in circuit.interface.ports.values():
            if port.isoutput():
                for assumption in self.assumptions:
                    # TODO: Chained assumptions?
                    assume_port = assumption.port
                    if isinstance(assume_port, SelectPath):
                        assume_port = assume_port[-1]
                    if assume_port is port:
                        pred = assumption.value
                        randval = constrained_random_bv(len(assume_port), pred)
                        code = self.make_poke(
                            len(actions) + i, Poke(port, randval))
                        for line in code:
                            main_body += f"  {line}\n"
                        break
        return main_body

    def add_guarantees(self, circuit, actions, i):
        main_body = ""
        for name, port in circuit.interface.ports.items():
            if port.isinput():
                for guarantee in self.guarantees:
                    guarantee_port = guarantee.port
                    if isinstance(guarantee_port, SelectPath):
                        guarantee_port = guarantee_port[-1]
                    if guarantee_port is port:
                        # TODO: Support functions too
                        code = utils.get_short_lambda_body_text(guarantee.value)
                        # TODO: More robust symbol replacer on AST
                        for port in circuit.interface.ports:
                            code = code.replace("and", "&&")
                            code = code.replace(port, f"top->{port}")
                        main_body += f"""\
    if (!({code})) {{
      std::cerr << std::endl;  // end the current line
      std::cerr << \"Got      : 0x\" << std::hex << top->{name} << std::endl;
      std::cerr << \"Expected : {code}" << std::endl;
      std::cerr << \"i        : {i}\" << std::endl;
      std::cerr << \"Port     : {name}\" << std::endl;
      #if VM_TRACE
        tracer->close();
      #endif
      exit(1);
    }}
"""
        return main_body
