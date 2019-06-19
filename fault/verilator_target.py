import logging
import fault
from .array import Array
from pathlib import Path
import subprocess
import magma as m
import fault.actions as actions
from fault.actions import Poke, Eval
from fault.verilog_target import VerilogTarget, verilog_name
import fault.value_utils as value_utils
import fault.verilator_utils as verilator_utils
from fault.select_path import SelectPath
from fault.wrapper import PortWrapper, InstanceWrapper
import math
from hwtypes import BitVector, SIntVector, AbstractBitVectorMeta
import subprocess
from fault.random import random_bv, constrained_random_bv
import fault.utils as utils
import platform
import os
import fault.expression as expression


def log(logger, message):
    """
    Helper function to ignore empty log messages
    """
    if message:
        for line in message.splitlines():
            logger(message)


# max_bits = 64 if platform.architecture()[0] == "64bit" else 32
max_bits = 32


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
                 flags=[], skip_compile=False, include_verilog_libraries=[],
                 include_directories=[], magma_output="coreir-verilog",
                 circuit_name=None, magma_opts={}, skip_verilator=False):
        """
        Params:
            `include_verilog_libraries`: a list of verilog libraries to include
            with the -v flag.  From the verilator docs:
                -v <filename>              Verilog library

            `include_directories`: a list of directories to include using the
            -I flag. From the the verilator docs:
                -I<dir>                    Directory to search for includes
        """
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         include_verilog_libraries, magma_output, magma_opts)
        self.flags = flags
        self.include_directories = include_directories

        # Compile the design using `verilator`, if not skip
        if not skip_verilator:
            driver_file = self.directory / Path(
                f"{self.circuit_name}_driver.cpp")
            verilator_cmd = verilator_utils.verilator_cmd(
                self.circuit_name, self.verilog_file.name,
                self.include_verilog_libraries, self.include_directories,
                driver_file.name, self.flags)
            result = self.run_from_directory(verilator_cmd)
            log(logging.info, result.stdout.decode())
            log(logging.info, result.stderr.decode())
            if result.returncode:
                raise Exception(f"Running verilator cmd {verilator_cmd} failed:"
                                f" {result.stderr.decode()}")
        self.debug_includes = set()
        verilator_version = subprocess.check_output("verilator --version",
                                                    shell=True)
        # Need to check version since they changed how internal signal access
        # works
        self.verilator_version = float(verilator_version.split()[1])

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
            return f"top->{verilog_name(value.port.name)}"

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
            name = verilog_name(action.port.name)

        # Special case poking internal registers
        is_reg_poke = isinstance(action.port, SelectPath) and \
            isinstance(action.port[-1], fault.WrappedVerilogInternalPort) \
            and action.port[-1].path == "outReg"

        if isinstance(action.value, BitVector) and \
                action.value.num_bits > max_bits:
            asserts = []
            for i in range(math.ceil(action.value.num_bits / max_bits)):
                value = action.value[i * max_bits:min(
                    (i + 1) * max_bits, action.value.num_bits)]
                asserts += [f"top->{name}[{i}] = {value};"]
            if is_reg_poke:
                raise NotImplementedError()
            return asserts
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
        ports = ", ".join(f"top->{verilog_name(port.name)}" for port in
                          action.ports)
        if ports:
            ports = ", " + ports
        return [f'printf("{action.format_str}"{ports});']

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
            name = verilog_name(action.port.name)
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
        name = verilog_name(action.clock.name)
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
        value = f"top->{verilog_name(action.value.name)}"
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

    def run_from_directory(self, cmd):
        logging.debug(cmd)
        return subprocess.run(cmd, cwd=self.directory, shell=True,
                              capture_output=True)

    def run(self, actions, verilator_includes=[], num_tests=0,
            _circuit=None):
        driver_file = self.directory / Path(f"{self.circuit_name}_driver.cpp")
        # Write the verilator driver to file.
        src = self.generate_code(actions, verilator_includes, num_tests,
                                 _circuit)
        with open(driver_file, "w") as f:
            f.write(src)
        # Run a series of commands: run the Makefile output by verilator, and
        # finally run the executable created by verilator.
        verilator_make_cmd = verilator_utils.verilator_make_cmd(
            self.circuit_name)
        result = self.run_from_directory(verilator_make_cmd)
        log(logging.debug, result.stdout.decode())
        assert not result.returncode, "Running verilator make_cmd_failed" \
            + result.stderr.decode()
        result = self.run_from_directory(
            f"/bin/bash -c \"set -e -o pipefail; ./obj_dir/V{self.circuit_name}"
            f" | tee ./obj_dir/{self.circuit_name}.log\"")
        log(logging.info, result.stdout.decode())
        log(logging.info, result.stderr.decode())
        assert not result.returncode, "Running verilator binary failed: " + \
            result.stderr.decode()

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
