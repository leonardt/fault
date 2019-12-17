import warnings
from fault.verilog_target import VerilogTarget, verilog_name
import magma as m
from pathlib import Path
import fault.actions as actions
from fault.actions import GetValue
from hwtypes import (BitVector, AbstractBitVectorMeta, AbstractBit,
                     AbstractBitVector)
import fault.value_utils as value_utils
from fault.select_path import SelectPath
from fault.wrapper import PortWrapper
from fault.subprocess_run import subprocess_run
import fault
import fault.expression as expression
from fault.real_type import RealKind, RealIn, RealOut, RealInOut
from fault.elect_type import ElectIn, ElectOut, ElectInOut
import os
from numbers import Number


SVTAB = '    '

src_tpl = """\
module {top_module};
{declarations}

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
    def __init__(self, circuit, circuit_name=None, directory="build/",
                 skip_compile=None, magma_output="coreir-verilog",
                 magma_opts=None, include_verilog_libraries=None,
                 simulator=None, timescale="1ns/1ns", clock_step_delay=5,
                 num_cycles=10000, dump_waveforms=True, dump_vcd=None,
                 no_warning=False, sim_env=None, ext_model_file=None,
                 ext_libs=None, defines=None, flags=None, inc_dirs=None,
                 ext_test_bench=False, top_module=None, ext_srcs=None,
                 use_input_wires=False, parameters=None, disp_type='on_error',
                 waveform_file=None, use_kratos=False,
                 value_file_name='get_value_file.txt',
                 value_file_var='__get_value_file_fid'):
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

        waveform_file: name of file to dump waveforms (default is
                       "waveform.vcd" for ncsim and "waveform.vpd" for vcs)

        use_kratos: If True, set the environment up for debugging in kratos

        value_file_name: name of the file to which results of "get_value"
                         commands should be dumped

        value_file_var: name of the integer variable to which the FID of
                        the value file used for "get_value" commands should
                        be store.
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

        # call the super constructor
        super().__init__(circuit, circuit_name, directory, skip_compile,
                         include_verilog_libraries, magma_output,
                         magma_opts, use_kratos=use_kratos)

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
        self.dump_waveforms = dump_waveforms
        if dump_vcd is not None:
            warnings.warn("tester.compile_and_run parameter dump_vcd is "
                          "deprecated; use dump_waveforms instead.",
                          DeprecationWarning)
            self.dump_waveforms = dump_vcd
        self.no_warning = no_warning
        self.declarations = []
        self.sim_env = sim_env if sim_env is not None else {}
        self.sim_env.update(os.environ)
        self.ext_model_file = ext_model_file
        self.ext_libs = ext_libs if ext_libs is not None else []
        self.defines = defines if defines is not None else {}
        self.flags = flags if flags is not None else []
        self.inc_dirs = inc_dirs if inc_dirs is not None else []
        self.ext_test_bench = ext_test_bench
        self.top_module = top_module if not use_kratos else "TOP"
        self.use_input_wires = use_input_wires
        self.parameters = parameters if parameters is not None else {}
        self.disp_type = disp_type
        self.waveform_file = waveform_file
        self.value_file_name = value_file_name
        self.value_file_var = value_file_var
        if self.waveform_file is None and self.dump_waveforms:
            if self.simulator == "vcs":
                self.waveform_file = "waveforms.vpd"
            elif self.simulator in {"ncsim", "iverilog", "vivado"}:
                self.waveform_file = "waveforms.vcd"
            else:
                raise NotImplementedError(self.simulator)
        self.use_kratos = use_kratos
        # check to see if runtime is installed
        if use_kratos:
            import sys
            assert sys.platform == "linux" or sys.platform == "linux2",\
                "Currently only linux is supported"
            if not fault.util.has_kratos_runtime():
                raise ImportError("Cannot find kratos-runtime in the system. "
                                  "Please do \"pip install kratos-runtime\" "
                                  "to install.")

    def add_decl(self, *decls):
        self.declarations.extend(decls)

    def make_name(self, port):
        if isinstance(port, PortWrapper):
            port = port.select_path
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
        elif value is fault.HiZ:
            value = "'Z"
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
        elif isinstance(value, expression.UnaryOp):
            operand = self.compile_expression(value.operand)
            op = value.op_str
            return f"{op} {operand}"
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
        # Build up the poke action, including delay
        retval = []
        retval += [f'{name} <= {value};']
        if action.delay is not None:
            retval += [f'#({action.delay}*1s);']
        return retval

    def make_delay(self, i, action):
        return [f'#({action.time}*1s);']

    def make_print(self, i, action):
        # build up argument list for the $write command
        args = []
        args.append(f'"{action.format_str}"')
        for port in action.ports:
            if isinstance(port, (Number, AbstractBit, AbstractBitVector)):
                args.append(f'{port}')
            else:
                args.append(f'{self.make_name(port)}')
        args = ', '.join(args)
        return [f'$write({args});']

    @classmethod
    def block_prim(cls, type_, hdr=None, cmds=None):
        # set defaults
        if cmds is None:
            cmds = []

        # build up code
        code = []

        # create the header
        if hdr is None:
            code += [f'{type_} begin']
        else:
            code += [f'{type_} ({hdr}) begin']

        # create the body
        code += [f'{SVTAB}{cmd}' for cmd in cmds]

        # create the footer
        code += [f'end']

        # return the code block
        return code

    @classmethod
    def if_prim(cls, cond, cmds):
        return cls.block_prim(type_='if', hdr=cond, cmds=cmds)

    @classmethod
    def for_loop_prim(cls, idx, loop_range, cmds):
        # read out parameters of the loop
        start = loop_range.start
        stop = loop_range.stop
        step = loop_range.step

        # build initialization part of expression
        init_expr = f'{idx} = {start}'

        # build condition part of expression
        if start <= stop:
            cond_expr = f'{idx} < {stop}'
        else:
            cond_expr = f'{idx} > {stop}'

        # build update part of expression
        if step == 1:
            up_expr = f'{idx}++'
        elif step == -1:
            up_expr = f'{idx}--'
        elif step > 0:
            up_expr = f'{idx} += {step}'
        else:
            up_expr = f'{idx} -= {-step}'

        # build code representing the entire loop
        hdr = f'{init_expr}; {cond_expr}; {up_expr}'

        # return code for the loop
        return cls.block_prim(type_='for', hdr=hdr, cmds=cmds)

    def make_loop(self, i, action):
        # process inner actions of the loop
        cmds = []
        for inner_action in action.actions:
            cmds += self.generate_action_code(i, inner_action)

        # declare a loop variable
        idx = f'{action.loop_var}'
        self.declarations.append(f"integer {idx};")

        # determine the range of the for loop
        loop_range = range(action.n_iter)

        # return code representing the for loop
        return self.for_loop_prim(idx=idx, loop_range=loop_range, cmds=cmds)

    @staticmethod
    def open_file_prim(path, var, mode):
        return f'{var} = $fopen("{path}", "{mode}");'

    def make_file_open(self, i, action):
        # make sure the file mode is supported
        if action.file.mode not in {'r', 'w'}:
            raise NotImplementedError(action.file.mode)

        # declare variable for reading file
        name = action.file.name_without_ext
        bit_size = action.file.chunk_size * 8 - 1
        self.declarations.append(f'reg [{bit_size}:0] {name}_in;')

        # declare variable to hold the file descriptor
        fd_var = f'{name}_file'
        self.declarations.append(f'integer {fd_var};')

        # determine path to file and read/write mode
        path = action.file.name
        mode = action.file.mode

        # generate code to open file
        code = []
        code += [self.open_file_prim(path=path, var=fd_var, mode=mode)]

        # check that file was opened correctly
        err_cmd = f'$error("Could not open file {path}: %0d", {fd_var});'
        code += self.if_prim(cond=f'!{fd_var}', cmds=[err_cmd])

        # return the code to open the file as a list of lines
        return code

    @staticmethod
    def close_file_prim(var):
        return f'$fclose({var});'

    def make_file_close(self, i, action):
        fd_var = f'{action.file.name_without_ext}_file'
        return [self.close_file_prim(var=fd_var)]

    @staticmethod
    def read_byte_prim(file_fd):
        return f'$fgetc({file_fd})'

    def make_file_read(self, i, action):
        # declare loop variable if needed
        idx = '__i'
        decl = f'integer {idx};'
        if decl not in self.declarations:
            self.declarations.append(decl)

        # figure out how to loop over bytes to be written
        chunk_size = action.file.chunk_size
        if action.file.endianness == 'big':
            for_range = range(chunk_size - 1, -1, -1)
        else:
            for_range = range(chunk_size)

        # determine command for reading one byte
        in_var = f'{action.file.name_without_ext}_in'
        fd_var = f'{action.file.name_without_ext}_file'
        rdcmd = f'{in_var} |= {self.read_byte_prim(fd_var)} << (8 * {idx});'

        # build up the code to implement the file read
        code = []
        code += [f'{in_var} = 0;']
        code += self.for_loop_prim(idx=idx, loop_range=for_range, cmds=[rdcmd])

        # return the code
        return code

    def write_byte_prim(self, file_fd, byte_expr):
        if self.simulator == 'iverilog':
            return f'$fputc({byte_expr}, {file_fd});'
        else:
            return f'$fwrite({file_fd}, "%c", {byte_expr});'

    @staticmethod
    def write_str_prim(file_fd, str_expr):
        return f'$fwrite({file_fd}, {str_expr});'

    def make_file_write(self, i, action):
        # declare loop variable if needed
        idx = '__i'
        decl = f'integer {idx};'
        if decl not in self.declarations:
            self.declarations.append(decl)

        # figure out how to loop over bytes to be written
        value = self.make_name(action.value)
        chunk_size = action.file.chunk_size
        mask_size = chunk_size * 8
        if action.file.endianness == 'big':
            loop_range = range(chunk_size - 1, -1, -1)
        else:
            loop_range = range(chunk_size)

        # determine command for writing one byte
        file_fd = f'{action.file.name_without_ext}_file'
        byte_expr = f"({value} >> (8 * {idx})) & {mask_size}'hFF"
        wrcmd = self.write_byte_prim(file_fd=file_fd, byte_expr=byte_expr)

        # return the loop code
        return self.for_loop_prim(idx=idx, loop_range=loop_range, cmds=[wrcmd])

    def make_get_value(self, i, action):
        # determine variable used for writing GetValue results
        file_fd = self.value_file_var

        # determine string representation of the value
        if self.is_float_like_port(action.port):
            fmt = '%0f'
        else:
            fmt = '%0d'
        str_expr = f'"{fmt}\\n", {self.make_name(action.port)}'

        # generate the command to write the string version of the signal to
        # the file
        wrcmd = self.write_str_prim(file_fd=file_fd, str_expr=str_expr)

        # return the code
        return [wrcmd]

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
                cond = f'!(({action.above} <= {name}) && ({name} <= {action.below}))'  # noqa
                err_msg = 'Expected %0f to %0f, got %0f'
                err_args = [action.above, action.below, name]
            else:
                # must be above
                cond = f'!({action.above} <= {name})'
                err_msg = 'Expected above %0f, got %0f'
                err_args = [action.above, name]
        else:
            if action.below is not None:
                # must be below
                cond = f'!({name} <= {action.below})'
                err_msg = 'Expected below %0f, got %0f'
                err_args = [action.below, name]
            else:
                # equality comparison
                if action.strict:
                    cond = f'!({name} === {value})'
                else:
                    cond = f'!({name} == {value})'
                err_msg = 'Expected %x, got %x'
                err_args = [value, name]

        # construct the body of the $error call
        err_fmt_str = f'"{err_hdr}.  {err_msg}."'
        err_body = [err_fmt_str] + err_args
        err_body = ','.join([str(elem) for elem in err_body])

        # return a snippet of verilog implementing the assertion
        err_cmd = f'$error({err_body});'
        return self.if_prim(cond=cond, cmds=[err_cmd])

    def make_eval(self, i, action):
        # Emulate eval by inserting a delay
        return ['#1;']

    def make_step(self, i, action):
        name = verilog_name(action.clock.name)
        code = []
        for step in range(action.steps):
            code.append(f"#{self.clock_step_delay} {name} ^= 1;")
        return code

    @classmethod
    def while_loop_prim(cls, cond, cmds):
        return cls.block_prim(type_='while', hdr=cond, cmds=cmds)

    def make_while(self, i, action):
        # compile the condition for the while loop
        cond = self.compile_expression(action.loop_cond)

        # process inner actions of the loop
        cmds = []
        for inner_action in action.actions:
            cmds += self.generate_action_code(i, inner_action)

        # return code for the while loop
        return self.while_loop_prim(cond=cond, cmds=cmds)

    def make_if(self, i, action):
        # compile the condition for the if statement
        cond = self.compile_expression(action.cond)

        # process inner actions of if statement
        if_cmds = []
        for inner_action in action.actions:
            if_cmds += self.generate_action_code(i, inner_action)

        # get code for if statement
        if_code = self.block_prim(type_='if', hdr=cond, cmds=if_cmds)

        # add code for else statement if needed
        if not action.else_actions:
            return if_code
        else:
            # process inner actions of else statement
            else_cmds = []
            for inner_action in action.else_actions:
                else_cmds += self.generate_action_code(i, inner_action)

            # get code for else statement
            else_code = self.block_prim(type_='else', cmds=else_cmds)

            # return code with with nice formatting
            return if_code[:-1] + ['end else begin'] + else_code[1:]

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
            connect_to = f"{name}"
            if isinstance(type_, m.ArrayKind) and \
                    isinstance(type_.T, m.BitKind):
                width_str = f"[{len(type_) - 1}:0] "
            if isinstance(type_, RealKind):
                t = "real"
            elif name in power_args.get("supply0s", []):
                t = "supply0"
            elif name in power_args.get("supply1s", []):
                t = "supply1"
            elif name in power_args.get("tris", []):
                t = "tri"
            elif type_.isoutput():
                t = "wire"
            elif type_.isinout() or (type_.isinput() and self.use_input_wires):
                # declare a reg and assign it to a wire
                # that wire will then be connected to the
                # DUT pin
                connect_to = self.input_wire(name)
                decls = [f'reg {width_str}{name};',
                         f'wire {width_str}{connect_to};',
                         f'assign {connect_to}={name};']
                decls = [f'{SVTAB}{decl}' for decl in decls]
                self.add_decl(*decls)

                # set the signal type to None to avoid re-declaring
                # connect_to
                t = None
            elif type_.isinput():
                t = "reg"
            else:
                raise NotImplementedError()

            # declare the signal that will be connected to the pin, if needed
            if t is not None:
                decl = f'{SVTAB}{t} {width_str}{connect_to};'
                self.add_decl(decl)

            # return the wiring statement describing how the testbench signal
            # is connected to the DUT
            return [f".{name}({connect_to})"]

    def generate_code(self, actions, power_args):
        # generate port list
        port_list = []
        for name, type_ in self.circuit.IO.ports.items():
            result = self.generate_port_code(name, type_, power_args)
            port_list.extend(result)

        # build up the body of the initial block
        initial_body = []

        # set up probing
        if self.dump_waveforms and self.simulator == "vcs":
            initial_body += [f'$vcdplusfile("{self.waveform_file}");',
                             f'$vcdpluson();',
                             f'$vcdplusmemon();']
        elif self.dump_waveforms and self.simulator in {"iverilog", "vivado"}:
            # https://iverilog.fandom.com/wiki/GTKWAVE
            initial_body += [f'$dumpfile("{self.waveform_file}");',
                             f'$dumpvars(0, dut);']

        # if we're using the GetValue feature, then we need to open a file to
        # which GetValue results will be written
        if any(isinstance(action, GetValue) for action in actions):
            has_get_value = True
            self.add_decl(f'{SVTAB}integer {self.value_file_var};')
            path = (Path(self.directory) / self.value_file_name).resolve()
            opcmd = self.open_file_prim(path=path,
                                        var=self.value_file_var,
                                        mode='w')
            initial_body.append(opcmd)
        else:
            has_get_value = False

        # handle all of user-specified actions in the testbench
        for i, action in enumerate(actions):
            initial_body += self.generate_action_code(i, action)

        # if we're using the GetValue feature, then we need to close the file
        # used to store GetValue results at the end of the simulation.
        if has_get_value:
            clcmd = self.close_file_prim(var=self.value_file_var)
            initial_body.append(clcmd)

        param_list = [f'.{name}({value})'
                      for name, value in self.parameters.items()]

        # add proper indentation and newlines to strings in the initial body
        initial_body = [f'{2*SVTAB}{elem}' for elem in initial_body]
        initial_body = '\n'.join(initial_body)

        # fill out values in the testbench template
        src = src_tpl.format(
            declarations='\n'.join(self.declarations),
            initial_body=initial_body,
            port_list=f',\n{2*SVTAB}'.join(port_list),
            param_list=f',\n{2*SVTAB}'.join(param_list),
            circuit_name=self.circuit_name,
            top_module=self.top_module if self.top_module is not None else
            f"{self.circuit_name}_tb"
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
            bin_err_str = 'Error'
        elif self.simulator == 'iverilog':
            # Compile simulation
            sim_cmd, bin_file = self.iverilog_cmd(sources=vlog_srcs)
            sim_err_str = ['syntax error', 'I give up.']
            # Run simulation
            bin_cmd = ['vvp', '-N', bin_file]
            bin_err_str = 'ERROR'
        else:
            raise NotImplementedError(self.simulator)

        # add any extra flags
        sim_cmd += self.flags

        # link the library over if using kratos to debug
        if self.use_kratos:
            self.link_kratos_lib()

        # compile the simulation
        subprocess_run(sim_cmd, cwd=self.directory, env=self.sim_env,
                       err_str=sim_err_str, disp_type=self.disp_type)

        # run the simulation binary (if applicable)
        if bin_cmd is not None:
            subprocess_run(bin_cmd, cwd=self.directory, env=self.sim_env,
                           err_str=bin_err_str, disp_type=self.disp_type)

        # post-process GetValue actions
        self.post_process_get_value_actions(actions)

    @staticmethod
    def is_float_like_port(port):
        return isinstance(port, (RealIn, RealOut, RealInOut,
                                 ElectIn, ElectOut, ElectInOut))

    def post_process_get_value_actions(self, actions):
        # extract the GetValue actions and return immediately
        # if there are none
        get_value_actions = [action for action in actions
                             if isinstance(action, GetValue)]
        if len(get_value_actions) == 0:
            return

        # read lines in the GetValue file
        with open(Path(self.directory) / self.value_file_name, 'r') as f:
            lines = f.readlines()

        # write results back into the "value" property of the action
        for line, action in zip(lines, get_value_actions):
            if self.is_float_like_port(action.port):
                action.value = float(line.strip())
            else:
                action.value = int(line.strip())

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

    @staticmethod
    def make_line(text, tabs=0, tab='    ', nl='\n'):
        return f'{tabs*tab}{text}{nl}'

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
        create_proj = f'create_project -force {proj_name} {proj_dir}'
        if proj_part is not None:
            create_proj += f' -part "{proj_part}"'
        tcl_cmds += [create_proj]

        # add source files and library files
        vlog_add_files = []
        vlog_add_files += [f'{src}' for src in sources]
        vlog_add_files += [f'{lib}' for lib in self.ext_libs]
        if len(vlog_add_files) > 0:
            vlog_add_files = ' '.join(vlog_add_files)
            tcl_cmds += [f'add_files "{vlog_add_files}"']

        # add include file search paths
        if len(self.inc_dirs) > 0:
            vlog_inc_dirs = ' '.join(f'{dir_}' for dir_ in self.inc_dirs)
            tcl_cmds += [f'set_property include_dirs "{vlog_inc_dirs}" [get_fileset sim_1]']  # noqa

        # add verilog `defines
        vlog_defs = []
        for key, val in self.defines.items():
            if val is not None:
                vlog_defs += [f'{key}={val}']
            else:
                vlog_defs += [f'{key}']
        if len(vlog_defs) > 0:
            vlog_defs = ' '.join(vlog_defs)
            tcl_cmds += [f'set_property -name "verilog_define" -value {{{vlog_defs}}} -objects [get_fileset sim_1]']  # noqa

        # set the name of the top module
        if self.top_module is None and not self.ext_test_bench:
            top = f'{self.circuit_name}_tb'
        else:
            top = self.top_module
        if top is not None:
            tcl_cmds += [f'set_property -name top -value {top} -objects [get_fileset sim_1]']  # noqa
        else:
            # have Vivado pick the top module automatically if not specified
            tcl_cmds += [f'update_compile_order -fileset sim_1']

        # run until $finish (as opposed to running for a certain amount of time)
        tcl_cmds += [f'set_property -name "xsim.simulate.runtime" -value "-all" -objects [get_fileset sim_1]']  # noqa

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

        # determine the name of the top module
        if self.top_module is None and not self.ext_test_bench:
            top = f'{self.circuit_name}_tb' if not self.use_kratos else "TOP"
        else:
            top = self.top_module

        # send name of top module to the simulator
        if top is not None:
            cmd += ['-top', f'{top}']

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
        cmd += ['-access', '+rwc']
        cmd += ['-notimingchecks']
        if self.no_warning:
            cmd += ['-neverwarn']

        # kratos flags
        if self.use_kratos:
            from kratos_runtime import get_ncsim_flag
            cmd += get_ncsim_flag().split()

        # return arg list
        return cmd

    def vivado_cmd(self, cmd_file):
        cmd = []

        # binary name
        cmd += ['vivado']

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

        if self.dump_waveforms:
            cmd += ['+vcs+vcdpluson', '-debug_pp']

        # return arg list and binary file location
        return cmd, './simv'

    def iverilog_cmd(self, sources):
        cmd = []

        # binary name
        cmd += ['iverilog']

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

        # source files
        cmd += [f'{src}' for src in sources]

        # return arg list and binary file location
        return cmd, bin_file
