import warnings
from fault.verilog_target import VerilogTarget
from .verilog_utils import verilog_name, is_nd_array
from .util import (is_valid_file_mode, file_mode_allows_reading,
                   file_mode_allows_writing)
import magma as m
from pathlib import Path
import fault.actions as actions
from fault.actions import FileOpen, FileClose, GetValue, Loop, If
from hwtypes import (BitVector, AbstractBitVectorMeta, AbstractBit,
                     AbstractBitVector, Bit)
import fault.value_utils as value_utils
from fault.select_path import SelectPath
from fault.wrapper import PortWrapper
from fault.subprocess_run import subprocess_run
import fault
import fault.expression as expression
from fault.ms_types import RealType
import os
from numbers import Number


src_tpl = """\
{timescale}
module {top_module};
{declarations}
{assigns}
{clock_drivers}

    {circuit_name} #(
        {param_list}
    ) dut (
        {port_list}
    );

    initial begin
{initial_body}
        #20 $finish;
    end

endmodule
"""


class SystemVerilogTarget(VerilogTarget):

    # Language properties of SystemVerilog used in generating code blocks
    BLOCK_START = 'begin'
    BLOCK_END = 'end'
    LOOP_VAR_TYPE = None

    def __init__(self, circuit, circuit_name=None, directory="build/",
                 skip_compile=None, magma_output="coreir-verilog",
                 magma_opts=None, include_verilog_libraries=None,
                 simulator=None, timescale="1ns/1ns", clock_step_delay=5,
                 num_cycles=10000, dump_waveforms=False, dump_vcd=None,
                 waveform_type=None, no_warning=False, sim_env=None,
                 ext_model_file=None, ext_libs=None, defines=None, flags=None,
                 inc_dirs=None, ext_test_bench=False, top_module=None,
                 ext_srcs=None, use_input_wires=False, parameters=None,
                 disp_type='on_error', waveform_file=None, coverage=False,
                 use_kratos=False, use_sva=False, skip_run=False,
                 no_top_module=False, vivado_use_system_verilog=True,
                 disable_ndarray=False):
        """
        circuit: a magma circuit

        circuit_name: the name of the circuit (default is circuit.name)

        directory: directory to use for generating collateral, buildling, and
                   running simulator

        skip_compile: (boolean) whether or not to compile the magma circuit

        magma_output: Set the output parameter to m.compile
                      (default coreir-verilog)

        magma_opts: Options dictionary for `magma.compile` command

        simulator: "ncsim", "vcs", "iverilog", or "vivado"

        timescale: Set the timescale for the verilog simulation
                   (default 1ns/1ns)

        clock_step_delay: Set the number of steps to delay for each step of the
                          clock

        sim_env: Environment variable definitions to use when running the
                 simulator.  If not provided, the value from os.environ will
                 be used.

        ext_model_file: If True, don't include the assumed model name in the
                        list of Verilog sources.  The assumption is that the
                        user has already taken care of this via
                        include_verilog_libraries.

        ext_libs: List of external files that should be treated as "libraries",
                  meaning that the simulator will look in them for module
                  definitions but not try to compile them otherwise.

        defines: Dictionary mapping Verilog DEFINE variable names to their
                 values.  If any value is None, that define simply defines
                 the variable without giving it a specific value.

        flags: List of additional arguments that should be passed to the
               simulator.

        inc_dirs: List of "include directories" to search for the `include
                  statement.

        ext_test_bench: If True, do not compile testbench actions into a
                        SystemVerilog testbench and instead simply run a
                        simulation of an existing (presumably manually
                        created) testbench.  Can be used to get started
                        integrating legacy testbenches into the fault
                        framework.

        top_module: Name of the top module in the design.  If the value is
                    None and ext_test_bench is False, then top_module will
                    automatically be filled with the name of the module
                    containing the generated testbench code.

        ext_srcs: Shorter alias for "include_verilog_libraries" argument.
                  If both "include_verilog_libraries" and ext_srcs are
                  specified, then the sources from include_verilog_libraries
                  will be processed first.

        use_input_wires: If True, drive DUT inputs through wires that are in
                         turn assigned to a reg.

        parameters: Dictionary of parameters to be defined for the DUT.

        disp_type: 'on_error', 'realtime'.  If 'on_error', only print if there
                   is an error.  If 'realtime', print out STDOUT as lines come
                   in, then print STDERR after the process completes.

        dump_waveforms: Enable tracing of internal values

        waveform_type: 'vcd', 'vpd', 'fsdb'.  Default for ncsim is 'vcd'. Default
                       for vcs is 'vpd'.

        waveform_file: name of file to dump waveforms (default is
                       "waveform.vcd" for ncsim and "waveform.vpd" for vcs)

        use_kratos: If True, set the environment up for debugging in kratos

        skip_run: If True, generate all the files (testbench, tcl, etc.) but do
                  not run the simulator.

        no_top_module: If True, do not specify a top module for simulation
                       (default is False, meaning *do* specify the top module)

        vivado_use_system_verilog: If True (default), mark Vivado source files
                                   as SystemVerilog so that more modern syntax
                                   is supported.

        disable_ndarray: If True, disable magma/fault support for
                         codegenerating verilog ndarrays (multi-dimensional
                         arrays of bits).
                         Default is False except when the simulator is
                         "iverilog" when it is always True (since iverilog does
                         not currently support unpacked arrays)
        """
        # set default for list of external sources
        if include_verilog_libraries is None:
            include_verilog_libraries = []
        if ext_srcs is None:
            ext_srcs = []
        include_verilog_libraries = include_verilog_libraries + ext_srcs

        # set default for there being an external model file
        if ext_model_file is None:
            ext_model_file = ext_test_bench

        # set default for whether magma compilation should happen
        if skip_compile is None:
            skip_compile = ext_model_file

        # set default for magma compilation options
        magma_opts = magma_opts if magma_opts is not None else {}

        if simulator == "iverilog":
            disable_ndarray = True
        if disable_ndarray:
            magma_opts["disable_ndarray"] = True
        self.disable_ndarray = disable_ndarray

        # call the super constructor
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         include_verilog_libraries, magma_output,
                         magma_opts, coverage=coverage, use_kratos=use_kratos)

        # set default for top_module.  this comes after the super constructor
        # invocation, because that is where the self.circuit_name is assigned
        if top_module is None:
            if use_kratos:
                top_module = 'TOP'
            elif ext_test_bench:
                top_module = f'{self.circuit_name}'
            else:
                top_module = f'{self.circuit_name}_tb'

        # sanity check
        if simulator is None:
            raise ValueError("Must specify simulator when using system-verilog"
                             " target")
        if simulator not in {"vcs", "ncsim", "iverilog", "vivado"}:
            raise ValueError(f"Unsupported simulator {simulator}")

        # save settings
        self.simulator = simulator
        self.timescale = timescale
        self.clock_step_delay = clock_step_delay
        self.num_cycles = num_cycles
        self.clock_drivers = []
        self.dump_waveforms = dump_waveforms
        if dump_vcd is not None:
            warnings.warn("tester.compile_and_run parameter dump_vcd is "
                          "deprecated; use dump_waveforms instead.",
                          DeprecationWarning)
            self.dump_waveforms = dump_vcd
        self.no_warning = no_warning
        self.declarations = {}  # dictionary keyed by signal name
        self.assigns = {}  # dictionary keyed by LHS name
        self.sim_env = sim_env if sim_env is not None else {}
        self.sim_env.update(os.environ)
        self.ext_model_file = ext_model_file
        self.ext_libs = ext_libs if ext_libs is not None else []
        self.defines = defines if defines is not None else {}
        self.flags = flags if flags is not None else []
        self.inc_dirs = inc_dirs if inc_dirs is not None else []
        self.ext_test_bench = ext_test_bench
        self.top_module = top_module
        self.use_input_wires = use_input_wires
        self.parameters = parameters if parameters is not None else {}
        self.disp_type = disp_type
        self.waveform_file = waveform_file
        self.use_sva = use_sva
        self.waveform_type = waveform_type
        if self.waveform_file is None and self.dump_waveforms:
            if self.simulator == "vcs":
                if self.waveform_type is None:
                    suffix = "vpd"
                else:
                    if self.waveform_type not in ["vpd", "fsdb"]:
                        raise ValueError("Only 'vpd' and 'fsdb' supported for "
                                         "vcs waveform type")
                    suffix = self.waveform_type
                self.waveform_file = f"waveforms.{self.waveform_type}"
            elif self.simulator in {"ncsim", "iverilog", "vivado"}:
                self.waveform_file = "waveforms.vcd"
            else:
                raise NotImplementedError(self.simulator)
        self.use_kratos = use_kratos
        self.skip_run = skip_run
        self.no_top_module = no_top_module
        self.vivado_use_system_verilog = vivado_use_system_verilog
        # check to see if runtime is installed
        if use_kratos:
            import sys
            assert sys.platform == "linux" or sys.platform == "linux2",\
                "Currently only linux is supported"
            if not fault.util.has_kratos_runtime():
                raise ImportError("Cannot find kratos-runtime in the system. "
                                  "Please do \"pip install kratos-runtime\" "
                                  "to install.")

    def add_decl(self, type_, name, exist_ok=False):
        if str(name) in self.declarations:
            if exist_ok:
                pass
            else:
                raise Exception(f'A declaration of name {name} already exists.')  # noqa
        else:
            # Note that order is preserved with Python 3.7 dictionary behavior
            self.declarations[str(name)] = (type_, name)

    def add_assign(self, lhs, rhs):
        if str(lhs) in self.assigns:
            raise Exception(f'The LHS signal {lhs} has already been assigned.')
        else:
            # Note that order is preserved with Python 3.7 dictionary behavior
            self.assigns[str(lhs)] = (lhs, rhs)

    def make_name(self, port):
        if isinstance(port, PortWrapper):
            port = port.select_path
        if isinstance(port, SelectPath):
            if len(port) > 2:
                name = f"dut.{port.system_verilog_path(self.disable_ndarray)}"
            else:
                # Top level ports assign to the external reg
                name = verilog_name(port[-1].name, self.disable_ndarray)
        elif isinstance(port, fault.WrappedVerilogInternalPort):
            name = f"dut.{port.path}"
        else:
            name = verilog_name(port.name, self.disable_ndarray)
        return name

    def process_peek(self, value):
        if isinstance(value.port, fault.WrappedVerilogInternalPort):
            return f"dut.{value.port.path}"
        elif isinstance(value.port, PortWrapper):
            path = value.port.select_path.system_verilog_path(
                self.disable_ndarray
            )
            return f"dut.{path}"
        return f"{value.port.name}"

    def make_var(self, i, action):
        if isinstance(action._type, AbstractBitVectorMeta):
            self.add_decl(f'reg [{action._type.size - 1}:0]', action.name)
            return []
        raise NotImplementedError(action._type)

    def make_file_scan_format(self, i, action):
        var_args = ", ".join(f"{var.name}" for var in action.args)
        fd_var = self.fd_var(action.file)
        return [f'$fscanf({fd_var}, "{action._format}", {var_args});']

    def process_value(self, port, value):
        if isinstance(value, Bit):
            value = f"1'b{int(value)}"
        elif isinstance(value, BitVector):
            value = f"{len(value)}'d{value.as_uint()}"
        elif isinstance(port, m.SInt) and value < 0:
            port_len = len(port)
            value = BitVector[port_len](value).as_uint()
            value = f"{port_len}'d{value}"
        elif value is fault.UnknownValue:
            value = "'X"
        elif value is fault.HiZ:
            value = "'Z"
        elif isinstance(value, actions.Peek):
            value = self.process_peek(value)
        elif isinstance(value, PortWrapper):
            path = value.select_path.system_verilog_path(self.disable_ndarray)
            value = f"dut.{path}"
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
            if op == "==":
                # Use strict eq
                op = "==="
            elif op == "!=":
                # Use strict neq
                op = "!=="
            return f"({left}) {op} ({right})"
        elif isinstance(value, expression.UnaryOp):
            operand = self.compile_expression(value.operand)
            op = value.op_str
            return f"{op} ({operand})"
        elif isinstance(value, PortWrapper):
            path = value.select_path.system_verilog_path(self.disable_ndarray)
            return f"dut.{path}"
        elif isinstance(value, actions.Peek):
            return self.process_peek(value)
        elif isinstance(value, actions.Var):
            value = value.name
        return value

    def make_poke(self, i, action):
        name = self.make_name(action.port)
        # For now we assume that verilog can handle big ints
        value = self.process_value(action.port, action.value)
        # Build up the poke action, including delay
        retval = []
        retval += [f'{name} <= {value};']
        if action.delay is not None:
            retval += [f'#({action.delay}*1s);']
        return retval

    def make_delay(self, i, action):
        return [f'#({action.time}*1s);']

    def _make_print_args(self, values):
        args = []
        for port in values:
            if isinstance(port, (Number, AbstractBit, AbstractBitVector)) and \
                    not isinstance(port, m.Bits):
                args.append(f'{port}')
            else:
                args.append(f'{self.make_name(port)}')
        return args

    def make_print(self, i, action):
        # build up argument list for the $write command
        args = [f'"{action.format_str}"']
        args += self._make_print_args(action.ports)
        # generate the command
        args = ', '.join(args)
        return [f'$write({args});']

    def make_loop(self, i, action):
        # loop variable has to be declared outside of the loop
        self.add_decl('integer', action.loop_var, exist_ok=True)
        return super().make_loop(i, action)

    def make_file_open(self, i, action):
        # make sure the file mode is supported
        if not is_valid_file_mode(action.file.mode):
            raise NotImplementedError(action.file.mode)

        # declare the file read variable if the file mode allows reading
        if file_mode_allows_reading(action.file.mode):
            bit_size = (action.file.chunk_size * 8) - 1
            in_ = self.in_var(action.file)
            self.add_decl(f'reg [{bit_size}:0]', in_)

        # declare the file descriptor variable
        fd = self.fd_var(action.file)
        self.add_decl('integer', fd)

        # return the command
        return [f'{fd} = $fopen("{action.file.name}", "{action.file.mode}");']

    def make_file_close(self, i, action):
        fd = self.fd_var(action.file)
        return [f'$fclose({fd});']

    def make_file_read(self, i, action):
        assert file_mode_allows_reading(action.file.mode), \
            f'File mode "{action.file.mode}" is not compatible with reading.'

        idx = '__i'
        fd = self.fd_var(action.file)
        in_ = self.in_var(action.file)

        return self.generate_action_code(i, [
            f'{in_} = 0;',
            Loop(loop_var=idx,
                 n_iter=action.file.chunk_size,
                 count='down' if action.file.endianness == 'big' else 'up',
                 actions=[
                     f'{in_} |= $fgetc({fd}) << (8 * {idx});'
                 ])
        ])

    def write_byte(self, fd, expr):
        if self.simulator == 'iverilog':
            return f'$fputc({expr}, {fd});'
        else:
            return f'$fwrite({fd}, "%c", {expr});'

    def make_file_write(self, i, action):
        assert file_mode_allows_writing(action.file.mode), \
            f'File mode "{action.file.mode}" is not compatible with writing.'

        idx = '__i'
        fd = self.fd_var(action.file)
        value = self.make_name(action.value)
        byte_expr = f"({value} >> (8 * {idx})) & 8'hFF"

        return self.generate_action_code(i, [
            Loop(loop_var=idx,
                 n_iter=action.file.chunk_size,
                 count='down' if action.file.endianness == 'big' else 'up',
                 actions=[
                     self.write_byte(fd, byte_expr)
                 ])
        ])

    def make_get_value(self, i, action):
        fd_var = self.fd_var(self.value_file)
        fmt = action.get_format()
        value = self.make_name(action.port)
        return [f'$fwrite({fd_var}, "{fmt}\\n", {value});']

    def make_assert(self, i, action):
        expr_str = self.compile_expression(action.expr)
        if self.use_sva:
            return [f'assert ({expr_str}) else $error("{expr_str} failed");']
        else:
            return [f'if (!({expr_str})) $error("{expr_str} failed");']

    def make_expect(self, i, action):
        # don't do anything if any value is OK
        if value_utils.is_any(action.value):
            return []

        # determine the exact name of the signal
        name = self.make_name(action.port)

        # TODO: add something like "make_read_name" and "make_write_name"
        # so that reading inout signals has more uniform behavior across
        # expect, peek, etc.
        if actions.is_inout(action.port):
            name = self.input_wire(name)

        # determine the name of the signal for debugging purposes
        if isinstance(action.port, SelectPath):
            debug_name = action.port[-1].name
        elif isinstance(action.port, fault.WrappedVerilogInternalPort):
            debug_name = name
        else:
            debug_name = action.port.name

        # determine the value to be checked
        value = self.process_value(action.port, action.value)

        # determine the condition and error body
        err_hdr = ''
        err_hdr += f'Failed on action={i} checking port {debug_name}'
        if action.traceback is not None:
            err_hdr += f' with traceback {action.traceback}'
        if action.above is not None:
            if action.below is not None:
                # must be in range
                cond = f'(({action.above} <= {name}) && ({name} <= {action.below}))'  # noqa
                err_msg = 'Expected %0f to %0f, got %0f'
                err_args = [action.above, action.below, name]
            else:
                # must be above
                cond = f'({action.above} <= {name})'
                err_msg = 'Expected above %0f, got %0f'
                err_args = [action.above, name]
        else:
            if action.below is not None:
                # must be below
                cond = f'({name} <= {action.below})'
                err_msg = 'Expected below %0f, got %0f'
                err_args = [action.below, name]
            else:
                # equality comparison
                if action.strict:
                    cond = f'({name} === {value})'
                else:
                    cond = f'({name} == {value})'
                err_msg = 'Expected %x, got %x'
                err_args = [value, name]
        if action.msg is not None:
            if isinstance(action.msg, str):
                err_msg += "\\n" + action.msg
            else:
                assert isinstance(action.msg, tuple)
                err_msg += "\\n" + action.msg[0]
                err_args += self._make_print_args(action.msg[1:])

        # construct the body of the $error call
        err_fmt_str = f'"{err_hdr}.  {err_msg}."'
        err_body = [err_fmt_str] + err_args
        err_body = ', '.join([str(elem) for elem in err_body])

        if self.use_sva:
            return [f'assert ({cond}) else $error({err_body});']
        else:
            # return a snippet of verilog implementing the assertion
            return self.make_if(i, If(f'!{cond}', [f'$error({err_body});']))

    def make_eval(self, i, action):
        # Emulate eval by inserting a delay
        return ['#1;']

    def make_step(self, i, action):
        name = verilog_name(action.clock.name, self.disable_ndarray)
        code = []
        for step in range(action.steps):
            code.append(f"#{self.clock_step_delay} {name} ^= 1;")
        return code

    def generate_recursive_port_code(self, name, type_, power_args):
        port_list = []
        if issubclass(type_, m.Array):
            for j in range(type_.N):
                result = self.generate_port_code(
                    name + "_" + str(j), type_.T, power_args
                )
                port_list.extend(result)
        elif issubclass(type_, m.Tuple):
            for k, t in zip(type_.keys(), type_.types()):
                result = self.generate_port_code(
                    name + "_" + str(k), t, power_args
                )
                port_list.extend(result)
        return port_list

    def generate_port_code(self, name, type_, power_args):
        is_array_of_non_bits = issubclass(type_, m.Array) and \
            not issubclass(type_.T, m.Bit)
        if is_nd_array(type_) and not self.disable_ndarray:
            outer_width = ""
            while not issubclass(type_.T, m.Digital):
                outer_width += f"[{type_.N - 1}:0]"
                type_ = type_.T
            inner_width = f"[{type_.N - 1}:0]"
            t = "reg" if type_.is_input() else "wire"
            self.add_decl(f'{t} {inner_width}', f'{name} {outer_width}')
            return [f".{name}({name})"]
        elif is_array_of_non_bits or issubclass(type_, m.Tuple):
            return self.generate_recursive_port_code(name, type_, power_args)
        else:
            width_str = ""
            connect_to = f"{name}"
            if issubclass(type_, m.Array) and \
                    issubclass(type_.T, m.Digital):
                width_str = f" [{len(type_) - 1}:0]"
            if issubclass(type_, RealType):
                t = "real"
            elif name in power_args.get("supply0s", []):
                t = "supply0"
            elif name in power_args.get("supply1s", []):
                t = "supply1"
            elif name in power_args.get("tris", []):
                t = "tri"
            elif type_.is_output():
                t = "wire"
            elif type_.is_inout() or \
                    (type_.is_input() and self.use_input_wires):
                # declare a reg and assign it to a wire
                # that wire will then be connected to the
                # DUT pin
                connect_to = self.input_wire(name)
                self.add_decl(f'reg{width_str}', f'{name}')
                self.add_decl(f'wire{width_str}', f'{connect_to}')
                self.add_assign(f'{connect_to}', f'{name}')

                # set the signal type to None to avoid re-declaring
                # connect_to
                t = None
            elif type_.is_input():
                t = "reg"
            else:
                raise NotImplementedError()

            # declare the signal that will be connected to the pin, if needed
            if t is not None:
                self.add_decl(f'{t}{width_str}', f'{connect_to}')

            # return the wiring statement describing how the testbench signal
            # is connected to the DUT
            return [f".{name}({connect_to})"]

    def generate_code(self, actions, power_args):
        # format the port list
        port_list = []
        for name, type_ in self.circuit.IO.ports.items():
            result = self.generate_port_code(name, type_, power_args)
            port_list.extend(result)
        port_list = f',\n{2*self.TAB}'.join(port_list)

        # build up the body of the initial block
        initial_body = []

        # set up probing
        if self.dump_waveforms and self.simulator == "vcs":
            if self.waveform_type == "vpd":
                initial_body += [f'$vcdplusfile("{self.waveform_file}");',
                                 f'$vcdpluson();',
                                 f'$vcdplusmemon();']
            if self.waveform_type == "fsdb":
                initial_body += [f'$fsdbDumpfile("{self.waveform_file}");',
                                 f'$fsdbDumpvars();']
        elif self.dump_waveforms and self.simulator in {"iverilog", "vivado"}:
            # https://iverilog.fandom.com/wiki/GTKWAVE
            initial_body += [f'$dumpfile("{self.waveform_file}");',
                             f'$dumpvars(0, dut);']

        # if we're using the GetValue feature, then we need to open a file to
        # which GetValue results will be written
        if any(isinstance(action, GetValue) for action in actions):
            actions = [FileOpen(self.value_file)] + actions
            actions += [FileClose(self.value_file)]

        # handle all of user-specified actions in the testbench
        for i, action in enumerate(actions):
            initial_body += self.generate_action_code(i, action)

        # format the paramter list
        param_list = [f'.{name}({value})'
                      for name, value in self.parameters.items()]
        param_list = f',\n{2*self.TAB}'.join(param_list)

        # add proper indentation and newlines to strings in the initial body
        initial_body = [f'{2*self.TAB}{elem}' for elem in initial_body]
        initial_body = '\n'.join(initial_body)

        # format declarations
        declarations = [f'{self.TAB}{type_} {name};'
                        for type_, name in self.declarations.values()]
        declarations = '\n'.join(declarations)

        # format assignments
        assigns = [f'{self.TAB}assign {lhs}={rhs};'
                   for lhs, rhs in self.assigns.values()]
        assigns = '\n'.join(assigns)

        # add timescale
        timescale = f'`timescale {self.timescale}'

        clock_drivers = self.TAB + "\n{self.TAB}".join(self.clock_drivers)

        # fill out values in the testbench template
        src = src_tpl.format(
            timescale=timescale,
            declarations=declarations,
            clock_drivers=clock_drivers,
            assigns=assigns,
            initial_body=initial_body,
            port_list=port_list,
            param_list=param_list,
            circuit_name=self.circuit_name,
            top_module=self.top_module
        )

        # return the string representing the system-verilog testbench
        return src

    def run(self, actions, power_args=None):
        # set defaults
        power_args = power_args if power_args is not None else {}

        # assemble list of sources files
        vlog_srcs = []
        if not self.ext_test_bench:
            tb_file = self.write_test_bench(actions=actions,
                                            power_args=power_args)
            vlog_srcs += [tb_file]
        if not self.ext_model_file:
            vlog_srcs += [self.verilog_file]
        vlog_srcs += self.include_verilog_libraries

        # generate simulator commands
        if self.simulator == 'ncsim':
            # Compile and run simulation
            cmd_file = self.write_ncsim_tcl()
            sim_cmd = self.ncsim_cmd(sources=vlog_srcs, cmd_file=cmd_file)
            sim_err_str = None
            # Skip "bin_cmd"
            bin_cmd = None
            bin_err_str = None
        elif self.simulator == 'vivado':
            # Compile and run simulation
            cmd_file = self.write_vivado_tcl(sources=vlog_srcs)
            sim_cmd = self.vivado_cmd(cmd_file=cmd_file)
            sim_err_str = ['CRITICAL WARNING', 'ERROR', 'Fatal', 'Error']
            # Skip "bin_cmd"
            bin_cmd = None
            bin_err_str = None
        elif self.simulator == 'vcs':
            # Compile simulation
            # TODO: what error strings are expected at this stage?
            sim_cmd, bin_file = self.vcs_cmd(sources=vlog_srcs)
            sim_err_str = None
            # Run simulation
            bin_cmd = [bin_file]
            bin_err_str = ['Error', 'Fatal']
        elif self.simulator == 'iverilog':
            # Compile simulation
            sim_cmd, bin_file = self.iverilog_cmd(sources=vlog_srcs)
            sim_err_str = ['syntax error', 'I give up.']
            # Run simulation
            bin_cmd = ['vvp', '-N', bin_file]
            bin_err_str = ['ERROR', 'FATAL']
        else:
            raise NotImplementedError(self.simulator)

        # link the library over if using kratos to debug
        if self.use_kratos:
            self.link_kratos_lib()

        if self.skip_run:
            return

        # compile the simulation
        subprocess_run(sim_cmd, cwd=self.directory, env=self.sim_env,
                       err_str=sim_err_str, disp_type=self.disp_type)

        # run the simulation binary (if applicable)
        if bin_cmd is not None:
            subprocess_run(bin_cmd, cwd=self.directory, env=self.sim_env,
                           err_str=bin_err_str, disp_type=self.disp_type)

        # post-process GetValue actions
        self.post_process_get_value_actions(actions)

    def write_test_bench(self, actions, power_args):
        # determine the path of the testbench file
        tb_file = self.directory / Path(f'{self.circuit_name}_tb.sv')
        tb_file = tb_file.absolute()

        # generate source code of test bench
        src = self.generate_code(actions, power_args)

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

        # return the path to the testbench location
        return tb_file

    @staticmethod
    def input_wire(name):
        return f'__{name}_wire'

    def link_kratos_lib(self):
        from kratos_runtime import get_lib_path
        lib_path = get_lib_path()
        dst_path = os.path.join(self.directory, os.path.basename(lib_path))
        if not os.path.isfile(dst_path):
            os.symlink(lib_path, dst_path)
        # also add the directory to the current LD_LIBRARY_PATH
        self.sim_env["LD_LIBRARY_PATH"] = os.path.abspath(self.directory)

    def write_ncsim_tcl(self):
        # construct the TCL commands to run the Incisive/Xcelium simulation
        tcl_cmds = []
        if self.dump_waveforms:
            tcl_cmds += [f'database -open -vcd vcddb -into {self.waveform_file} -default -timescale ps']  # noqa
            tcl_cmds += [f'probe -create -all -vcd -depth all']
        tcl_cmds += [f'run {self.num_cycles}ns']
        tcl_cmds += [f'quit']

        # write the command file
        cmd_file = Path(f'{self.circuit_name}_cmd.tcl')
        with open(self.directory / cmd_file, 'w') as f:
            f.write('\n'.join(tcl_cmds))

        # return the path to the command file
        return cmd_file

    def write_vivado_tcl(self, sources=None, proj_name='project', proj_dir=None,
                         proj_part=None):
        # set defaults
        if sources is None:
            sources = []
        if proj_dir is None:
            proj_dir = f'{proj_name}'

        # build up a list of commands to run a simulation with Vivado
        tcl_cmds = []

        # create the project
        create_proj = f'create_project -force {{{proj_name}}} {{{proj_dir}}}'
        if proj_part is not None:
            create_proj += f' -part {{{proj_part}}}'
        tcl_cmds += [create_proj]

        # add source files and library files
        vlog_add_files = []
        vlog_add_files += [f'{{{src}}}' for src in sources]
        vlog_add_files += [f'{{{lib}}}' for lib in self.ext_libs]
        if len(vlog_add_files) > 0:
            vlog_add_files = ' '.join(vlog_add_files)
            tcl_cmds += [f'add_files [list {vlog_add_files}]']

        # mark Verilog files as SystemVerilog so that more modern
        # syntax is supported
        if self.vivado_use_system_verilog:
            tcl_cmds += [f'set_property file_type SystemVerilog [get_files [list {vlog_add_files}]]']  # noqa

        # add include file search paths
        if len(self.inc_dirs) > 0:
            vlog_inc_dirs = ' '.join(f'{{{dir_}}}' for dir_ in self.inc_dirs)
            vlog_inc_dirs = f'[list {vlog_inc_dirs}]'
            tcl_cmds += [f'set_property include_dirs {vlog_inc_dirs} [get_fileset sim_1]']  # noqa

        # add verilog `defines
        vlog_defs = []
        for key, val in self.defines.items():
            if val is not None:
                vlog_defs += [f'{{{key}={val}}}']
            else:
                vlog_defs += [f'{{{key}}}']
        if len(vlog_defs) > 0:
            vlog_defs = ' '.join(vlog_defs)
            vlog_defs = f'[list {vlog_defs}]'
            tcl_cmds += [f'set_property -name verilog_define -value {vlog_defs} -objects [get_fileset sim_1]']  # noqa

        # set the name of the top module
        if not self.no_top_module:
            tcl_cmds += [f'set_property -name top -value {{{self.top_module}}} -objects [get_fileset sim_1]']  # noqa
        else:
            tcl_cmds += ['update_compile_order -fileset sim_1']

        # run until $finish (as opposed to running for a certain amount of time)
        tcl_cmds += [f'set_property -name xsim.simulate.runtime -value -all -objects [get_fileset sim_1]']  # noqa

        # run the simulation
        tcl_cmds += ['launch_simulation']

        # write the command file
        cmd_file = Path(f'{self.circuit_name}_cmd.tcl')
        with open(self.directory / cmd_file, 'w') as f:
            f.write('\n'.join(tcl_cmds))

        # return the path to the command file
        return cmd_file

    def def_args(self, prefix):
        retval = []
        for key, val in self.defines.items():
            def_arg = f'{prefix}{key}'
            if val is not None:
                def_arg += f'={val}'
            retval += [def_arg]
        return retval

    def ncsim_cmd(self, sources, cmd_file):
        cmd = []

        # binary name
        cmd += ['irun']

        # add any extra flags
        cmd += self.flags

        # send name of top module to the simulator
        if not self.no_top_module:
            cmd += ['-top', f'{self.top_module}']

        # timescale
        cmd += ['-timescale', f'{self.timescale}']

        # TCL commands
        cmd += ['-input', f'{cmd_file}']

        # source files
        cmd += [f'{src}' for src in sources]

        # library files
        for lib in self.ext_libs:
            cmd += ['-v', f'{lib}']

        # include directory search path
        for dir_ in self.inc_dirs:
            cmd += ['-incdir', f'{dir_}']

        # define variables
        cmd += self.def_args(prefix='+define+')

        # misc flags
        if self.dump_waveforms:
            cmd += ["-access", "r"]
        cmd += ['-notimingchecks']
        if self.no_warning:
            cmd += ['-neverwarn']

        # kratos flags
        if self.use_kratos:
            from kratos_runtime import get_ncsim_flag
            cmd += get_ncsim_flag().split()

        # coverage flags
        if self.coverage:
            cmd += ["-coverage", "b", "-covoverwrite"]

        # return arg list
        return cmd

    def vivado_cmd(self, cmd_file):
        cmd = []

        # binary name
        cmd += ['vivado']

        # add any extra flags
        cmd += self.flags

        # run from an external script
        cmd += ['-mode', 'batch']

        # specify path to script
        cmd += ['-source', f'{cmd_file}']

        # turn off annoying output
        cmd += ['-nolog']
        cmd += ['-nojournal']

        # return arg list
        return cmd

    def vcs_cmd(self, sources):
        cmd = []

        # binary name
        cmd += ['vcs']

        # add any extra flags
        cmd += self.flags

        # timescale
        cmd += [f'-timescale={self.timescale}']

        # source files
        cmd += [f'{src}' for src in sources]

        # library files
        for lib in self.ext_libs:
            cmd += ['-v', f'{lib}']

        # include directory search path
        for dir_ in self.inc_dirs:
            cmd += [f'+incdir+{dir_}']

        # define variables
        cmd += self.def_args(prefix='+define+')

        # misc flags
        cmd += ['-sverilog']
        cmd += ['-full64']
        cmd += ['+v2k']
        cmd += ['-LDFLAGS']
        cmd += ['-Wl,--no-as-needed']

        # kratos flags
        if self.use_kratos:
            # +vpi -load libkratos-runtime.so:initialize_runtime_vpi -acc+=rw
            from kratos_runtime import get_vcs_flag
            cmd += get_vcs_flag().split()

        # not supported yet
        if self.coverage:
            raise NotImplementedError("coverage in vcs is not implemented yet")

        if self.dump_waveforms:
            cmd += ['-debug_pp']

            if self.waveform_type == "vcd":
                cmd += ['+vcs+vcdpluson']

        # specify top module
        if not self.no_top_module:
            cmd += ['-top', f'{self.top_module}']

        # return arg list and binary file location
        return cmd, './simv'

    def iverilog_cmd(self, sources):
        cmd = []

        # binary name
        cmd += ['iverilog']

        # add any extra flags
        cmd += self.flags

        # output file
        bin_file = f'{self.circuit_name}_tb'
        cmd += [f'-o{bin_file}']

        # look for *.v and *.sv files, if we're using library directories
        if len(self.ext_libs) > 0:
            cmd += ['-Y.v', '-Y.sv']

        # Icarus verilog does not have an option like "-v" that allows
        # individual files to be included, so the best we can do is gather a
        # list of unique library directories
        unq_lib_dirs = {}
        for lib in self.ext_libs:
            parent_dir = Path(lib).parent
            if parent_dir not in unq_lib_dirs:
                unq_lib_dirs[parent_dir] = None
        cmd += [f'-y{unq_lib_dir}' for unq_lib_dir in unq_lib_dirs]

        # include directory search path
        for dir_ in self.inc_dirs:
            cmd += [f'-I{dir_}']

        # define variables
        cmd += self.def_args(prefix='-D')

        # misc flags
        cmd += ['-g2012']

        # set the top module.  note that the '-s' option must
        # come before the source file list.
        if not self.no_top_module:
            cmd += ['-s', f'{self.top_module}']

        # source files
        cmd += [f'{src}' for src in sources]

        # return arg list and binary file location
        return cmd, bin_file


class SynchronousSystemVerilogTarget(SystemVerilogTarget):
    def __init__(self, *args, clock=None, **kwargs):
        if clock is None:
            raise ValueError("Clock required")

        super().__init__(*args, **kwargs)
        name = verilog_name(clock.name, self.disable_ndarray)
        self.clock_drivers.append(
            f"always #{self.clock_step_delay} {name} = ~{name};"
        )

    def make_step(self, i, action):
        return [f"#{self.clock_step_delay * action.steps}"]
