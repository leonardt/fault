import fault
from pathlib import Path
import magma as m
from .util import (is_valid_file_mode, file_mode_allows_reading,
                   file_mode_allows_writing)
import fault.actions as actions
from fault.actions import Poke, Eval, FileOpen, FileClose, GetValue, Loop, If
from fault.verilog_target import VerilogTarget
from fault.verilog_utils import verilator_name
import fault.value_utils as value_utils
from fault.verilator_utils import (verilator_make_cmd, verilator_comp_cmd,
                                   verilator_version)
from fault.select_path import SelectPath
from fault.wrapper import PortWrapper, InstanceWrapper
import math
from hwtypes import BitVector, AbstractBitVectorMeta, Bit
from fault.random import constrained_random_bv
from fault.subprocess_run import subprocess_run
import fault.utils as utils
import fault.expression as expression
import platform
import os
import glob


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

// function to write_coverage
#ifdef _VERILATED_COV_H_
void write_coverage() {{
     VerilatedCov::write("logs/coverage.dat");
}}

#endif

#if VM_TRACE
VerilatedVcdC* tracer;
#endif

int main(int argc, char **argv) {{
  Verilated::commandArgs(argc, argv);
  V{circuit_name}* top = new V{circuit_name};
  {kratos_start_call}
#if VM_TRACE
  Verilated::traceEverOn(true);
  tracer = new VerilatedVcdC;
  top->trace(tracer, 99);
  mkdir("logs", S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
  tracer->open("logs/{circuit_name}.vcd");
#endif

{main_body}

#if VM_TRACE
  tracer->dump(main_time);
  tracer->close();
#endif
  {kratos_exit_call}

#ifdef _VERILATED_COV_H_
    write_coverage();
#endif

}}
"""  # nopep8


class VerilatorTarget(VerilogTarget):

    # Language properties of C used in generating code blocks
    BLOCK_START = '{'
    BLOCK_END = '}'
    LOOP_VAR_TYPE = 'int'

    def __init__(self, circuit, directory="build/",
                 flags=None, skip_compile=False, include_verilog_libraries=None,
                 include_directories=None, magma_output="coreir-verilog",
                 circuit_name=None, magma_opts=None, skip_verilator=False,
                 disp_type='on_error', coverage=False, use_kratos=False):
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
        self.use_kratos = use_kratos
        if use_kratos:
            try:
                import kratos_runtime
            except ImportError:
                raise ImportError("Cannot find kratos-runtime in the system. "
                                  "Please do \"pip install kratos-runtime\" "
                                  "to install.")

        # Call super constructor
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         include_verilog_libraries, magma_output, magma_opts,
                         coverage=coverage)

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
                verilator_flags=flags,
                coverage=self.coverage,
                use_kratos=use_kratos
            )
            # shell=True since 'verilator' is actually a shell script
            subprocess_run(comp_cmd, cwd=self.directory, shell=True,
                           disp_type=self.disp_type)

        # Initialize variables
        self.verilator_version = verilator_version(disp_type=self.disp_type)


    def _make_assert(self, got, expected, i, port, user_msg):
        kratos_exit_call = ""
        if self.use_kratos:
            kratos_exit_call = "teardown_runtime();"
        user_msg_str = ""
        if user_msg:
            arg_str = ""
            if len(user_msg) > 1:
                arg_str += f", {', '.join(user_msg[1:])}"
            user_msg_str += f"printf(\"{user_msg[0]}\"{arg_str});"
        return f"""\
      if (({got}) != ({expected})) {{
        std::cerr << std::endl;  // end the current line
        std::cerr << \"Got      : 0x\" << std::hex << ({got}) << std::endl;
        std::cerr << \"Expected : 0x\" << std::hex << ({expected}) << std::endl;
        std::cerr << \"i        : \" << std::dec << {i} << std::endl;
        std::cerr << \"Port     : \" << {port} << std::endl;
        {user_msg_str}
#if VM_TRACE
        // Dump one more timestep so we see the current values
        tracer->dump(main_time);
        tracer->close();
#endif
        {kratos_exit_call}
        exit(1);
      }}
    """

    def get_verilator_prefix(self):
        if self.verilator_version > 3.874:
            return f"{self.circuit_name}"
        else:
            return f"v"

    def process_peek(self, value):
        if isinstance(value.port, fault.WrappedVerilogInternalPort):
            path = value.port.path.replace(".", "->")
            return f"top->{self.get_verilator_prefix()}->{path}"
        elif isinstance(value.port, PortWrapper):
            return f"top->{value.port.select_path.verilator_path}"
        return f"top->{verilator_name(value.port.name)}"

    def process_value(self, port, value):
        if isinstance(value, expression.Expression):
            return self.compile_expression(value)
        if isinstance(value, Bit):
            return int(value)
        if isinstance(value, (int, BitVector)) and value < 0:
            return self.process_signed_values(port, value)
        if isinstance(value, (int, BitVector)):
            return value
        if isinstance(value, actions.Var):
            return value.name
        if isinstance(value, actions.FileRead):
            mask = "FF" * value.file.chunk_size
            value = " | ".join(f"{value.file.name_without_ext}_in[{i}]"
                               for i in range(value.file.chunk_size))
            return f"({value}) & 0x{mask}"
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
        elif isinstance(value, expression.UnaryOp):
            operand = self.compile_expression(value.operand)
            op = value.op_str
            return f"{op} ({operand})"
        elif isinstance(value, PortWrapper):
            return f"top->{value.select_path.verilator_path}"
        elif isinstance(value, actions.Peek):
            return self.process_peek(value)
        elif isinstance(value, actions.Var):
            return value.name
        return value

    def process_bitwise_assign(self, port, name, value):
        # Bitwise assign done using masking
        if isinstance(port, SelectPath):
            port = port[-1]
        if isinstance(port, fault.WrappedVerilogInternalPort):
            return value
        if isinstance(port.name, m.ref.ArrayRef) and \
                issubclass(port.name.array.T, m.Digital):
            i = port.name.index
            value = f"(top->{name} & ~(1UL << {i})) | ({value} << {i})"
        return value

    def process_bitwise_expect(self, port, value):
        if isinstance(port, SelectPath):
            port = port[-1]
        if isinstance(port, fault.WrappedVerilogInternalPort):
            return value
        if isinstance(port.name, m.ref.ArrayRef) and \
                issubclass(port.name.array.T, m.Digital):
            # Extract bit
            i = port.name.index
            value = f"({value} >> {i}) & 1"
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
            value = self.process_value(action.port, value)
            value = self.process_bitwise_assign(action.port, name, value)
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

    def _make_print_args(self, ports):
        port_names = []
        prefix = self.get_verilator_prefix()
        for port in ports:
            if isinstance(port, fault.WrappedVerilogInternalPort):
                path = port.path.replace(".", "->")
                name = f"{prefix}->{path}"
            elif isinstance(port, PortWrapper):
                port = port.select_path
                name = port.verilator_path
                if len(port) > 2:
                    name = f"{prefix}->" + name
            else:
                name = verilator_name(port.name)
            port_names.append(name)
        return tuple(f"top->{name}" for name in port_names)

    def make_print(self, i, action):
        ports = self._make_print_args(action.ports)
        if len(ports) != 0:
            ports_str = ", " + ", ".join(ports)
        else:
            ports_str = ""
        return [f'printf("{action.format_str}"{ports_str});']

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
            debug_name = action.port[-1].debug_name
        else:
            name = verilator_name(action.port.name)
            debug_name = action.port.debug_name
        value = action.value
        if isinstance(value, actions.Peek):
            value = self.process_peek(value)
        elif isinstance(value, PortWrapper):
            value = f"top->{prefix}->" + value.select_path.verilator_path

        user_msg = ()
        if action.msg is not None:
            if isinstance(action.msg, str):
                user_msg += (action.msg, )
            else:
                assert isinstance(action.msg, tuple)
                user_msg += (action.msg[0], )
                user_msg += self._make_print_args(action.msg[1:])

        if isinstance(action.value, BitVector) and \
                action.value.num_bits > max_bits:
            asserts = []
            # For some reason, verilator chunks it by 32 instead of max_bits
            slice_range = 32
            for j in range(math.ceil(action.value.num_bits / slice_range)):
                value = action.value[j * slice_range:min(
                    (j + 1) * slice_range, action.value.num_bits)]
                asserts.append(self._make_assert(
                    f"((unsigned int) top->{name}[{j}])", 
                    f"((unsigned int) {value})", i, f"\"{debug_name}\"",
                    user_msg))
            return asserts
        else:
            value = self.process_value(action.port, value)
            port_value = f"top->{name}"
            port_value = self.process_bitwise_expect(action.port, port_value)

            port = action.port
            if isinstance(port, SelectPath):
                port = port[-1]
            elif isinstance(port, fault.WrappedVerilogInternalPort):
                port = port.type_
            if isinstance(port, m.Digital):
                port_len = 1
            else:
                port_len = len(port)
            mask = (1 << port_len) - 1

            return [self._make_assert(f"((unsigned int) {port_value})",
                                      f"(unsigned int) ({value} & {mask})", i,
                                      f"\"{debug_name}\"", user_msg)]

    def make_eval(self, i, action):
        return ["top->eval();", "#if VM_TRACE", "tracer->dump(main_time);",
                "main_time++;", "#endif"]

    def make_step(self, i, action):
        name = verilator_name(action.clock.name)
        code = []
        code.append("top->eval();")
        for step in range(action.steps):
            code.append("#if VM_TRACE")
            code.append("tracer->dump(main_time);")
            code.append("#endif")
            code.append(f"top->{name} ^= 1;")
            code.append("top->eval();")
            code.append("main_time += 5;")
        return code

    def make_file_open(self, i, action):
        # make sure the file mode is supported
        if not is_valid_file_mode(action.file.mode):
            raise NotImplementedError(action.file.mode)

        # declare the file read variable if the file mode allows reading
        if file_mode_allows_reading(action.file.mode):
            in_ = self.in_var(action.file)
            decl_rd_var = [f'char {in_}[{action.file.chunk_size}] = {{0}};']
        else:
            decl_rd_var = []

        fd = self.fd_var(action.file)
        err_msg = f'Could not open file {action.file.name}'

        return self.generate_action_code(i, decl_rd_var + [
            f'FILE *{fd} = fopen("{action.file.name}", "{action.file.mode}");',
            If(f'{fd} == NULL', [
                f'std::cout << "{err_msg}" << std::endl;',
                f'return 1;'
            ])
        ])

    def make_file_close(self, i, action):
        fd_var = self.fd_var(action.file)
        return [f'fclose({fd_var});']

    def write_byte(self, fd, expr):
        return f'fputc({expr}, {fd})'

    def make_file_write(self, i, action):
        assert file_mode_allows_writing(action.file.mode), \
            f'File mode {action.file.mode} is not compatible with writing.'

        idx = 'i'
        fd = self.fd_var(action.file)
        value = f'top->{verilator_name(action.value.name)}'
        byte_expr = f'({value} >> ({idx} * 8)) & 0xFF'
        err_msg = f'Error writing to {action.file.name_without_ext}'

        return self.generate_action_code(i, [
            Loop(loop_var=idx,
                 n_iter=action.file.chunk_size,
                 count='down' if action.file.endianness == 'big' else 'up',
                 actions=[
                     'int result = ' + self.write_byte(fd, byte_expr) + ';',
                     If(f'result == EOF', [
                         f'std::cout << "{err_msg}" << std::endl;',
                         'break;'
                     ]),
                 ])
        ])

    def make_file_read(self, i, action):
        assert file_mode_allows_reading(action.file.mode), \
            f'File mode {action.file.mode} is not compatible with reading.'

        idx = 'i'
        fd = self.fd_var(action.file)
        in_ = self.in_var(action.file)
        err_msg = f'Reached end of file {action.file.name_without_ext}'

        return self.generate_action_code(i, [
            Loop(loop_var=idx,
                 n_iter=action.file.chunk_size,
                 count='down' if action.file.endianness == 'big' else 'up',
                 actions=[
                     f'int result = fgetc({fd});',
                     If(f'result == EOF', [
                         f'std::cout << "{err_msg}" << std::endl;',
                         'break;'
                     ]),
                     f'{in_}[{idx}] = result;'
                 ])
        ])

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

    def make_get_value(self, i, action):
        fd_var = self.fd_var(self.value_file)
        fmt = action.get_format()
        value = f'top->{verilator_name(action.port.name)}'
        return [f'fprintf({fd_var}, "{fmt}\\n", {value});']

    def make_assert(self, i, action):
        expr_str = self.compile_expression(action.expr)
        return f"""
if (!({expr_str})) {{
    std::cerr << "{expr_str} failed" << std::endl;
    #if VM_TRACE
      tracer->close();
    #endif
    exit(1);
}}
    """.splitlines()

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

        # if we're using the GetValue feature, then we need to open/close a
        # file in which GetValue results will be written
        if any(isinstance(action, GetValue) for action in actions):
            actions = [FileOpen(self.value_file)] + actions
            actions += [FileClose(self.value_file)]

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

        # Add includes from sub-modules (for internal wire selects).
        headers = glob.glob(os.path.join(self.directory, "obj_dir") + "/V*.h")
        headers = list(map(os.path.basename, headers))
        includes += [f'"{header}"' for header in headers]

        if self.coverage:
            includes += ["\"verilated_cov.h\""]

        includes_src = "\n".join(["#include " + i for i in includes])
        if self.use_kratos:
            includes_src += "\nvoid initialize_runtime();\n"
            includes_src += "void teardown_runtime();\n"
            kratos_start_call = "initialize_runtime();"
            kratos_exit_call = "teardown_runtime();"
        else:
            kratos_start_call = ""
            kratos_exit_call = ""

        src = src_tpl.format(
            includes=includes_src,
            main_body=main_body,
            circuit_name=self.circuit_name,
            kratos_start_call=kratos_start_call,
            kratos_exit_call=kratos_exit_call
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

        # if use kratos, symbolic link the library to dest folder
        if self.use_kratos:
            from kratos_runtime import get_lib_path
            lib_name = os.path.basename(get_lib_path())
            dst_path = os.path.abspath(os.path.join(self.directory, "obj_dir",
                                                    lib_name))
            if not os.path.isfile(dst_path):
                os.symlink(get_lib_path(), dst_path)
            # add ld library path
            env = {"LD_LIBRARY_PATH": os.path.dirname(dst_path)}
        else:
            env = None

        # Run makefile created by verilator
        make_cmd = verilator_make_cmd(self.circuit_name)
        subprocess_run(make_cmd, cwd=self.directory, disp_type=self.disp_type)

        # create the logs folder if necessary
        logs = Path(self.directory) / "logs"
        if not os.path.isdir(logs):
            os.mkdir(logs)

        # Run the executable created by verilator and write the standard
        # output to a logfile for later review or processing
        exe_cmd = [f'./obj_dir/V{self.circuit_name}']
        result = subprocess_run(exe_cmd, cwd=self.directory,
                                disp_type=self.disp_type,
                                env=env)
        log = Path(self.directory) / 'obj_dir' / f'{self.circuit_name}.log'
        with open(log, 'w') as f:
            f.write(result.stdout)

        # post-process GetValue actions
        self.post_process_get_value_actions(actions)

    def add_assumptions(self, circuit, actions, i):
        main_body = ""
        for port in circuit.interface.ports.values():
            if port.is_output():
                for assumption in self.assumptions:
                    # TODO: Chained assumptions?
                    assume_port = assumption.port
                    if isinstance(assume_port, SelectPath):
                        assume_port = assume_port[-1]
                    if assume_port is port:
                        pred = assumption.value
                        if assumption.has_randvals:
                            randval = next(assumption.randvals)[str(port.name)]
                        else:
                            randval = constrained_random_bv(len(assume_port),
                                                            pred)
                        code = self.make_poke(
                            len(actions) + i, Poke(port, randval))
                        for line in code:
                            main_body += f"  {line}\n"
                        break
        return main_body

    def add_guarantees(self, circuit, actions, i):
        main_body = ""
        for name, port in circuit.interface.ports.items():
            if port.is_input():
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


class SynchronousVerilatorTarget(VerilatorTarget):
    def __init__(self, *args, clock=None, **kwargs):
        if clock is None:
            raise ValueError("Clock required")
        self.clock = verilator_name(clock.name)

    def make_step(self, i, action):
        code = []
        for _ in range(action.steps):
            code.append("#if VM_TRACE")
            code.append("tracer->dump(main_time);")
            code.append("#endif")
            code.append(f"top->{self.clock} ^= 1;")
            code.append("top->eval();")
            code.append("main_time += 5;")
        return code
