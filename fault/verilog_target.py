from abc import abstractmethod
import magma as m
from .file import File
from fault.target import Target
from pathlib import Path
import fault.actions as actions
from fault.util import flatten
import os
from fault.select_path import SelectPath


class VerilogTarget(Target):
    """
    Provides reuseable target logic for compiling circuits into verilog files.
    """

    TAB = '    '
    BLOCK_START = None
    BLOCK_END = None
    LOOP_VAR_TYPE = None

    def __init__(self, circuit, circuit_name=None, directory="build/",
                 skip_compile=False, include_verilog_libraries=None,
                 magma_output="verilog", magma_opts=None, coverage=False,
                 use_kratos=False, value_file_name='get_value_file.txt'):
        super().__init__(circuit)

        self.circuit_name = circuit_name
        if self.circuit_name is None:
            self.circuit_name = self.circuit.name

        self.directory = Path(directory)
        os.makedirs(directory, exist_ok=True)

        self.skip_compile = skip_compile

        if include_verilog_libraries is None:
            include_verilog_libraries = []
        self.include_verilog_libraries = include_verilog_libraries

        self.magma_output = magma_output
        self.magma_opts = magma_opts if magma_opts is not None else {}
        if "user_namespace" in self.magma_opts and circuit_name is None:
            # If user provides a circuit name, we will not change it (assumes
            # they include the user_namespace)
            self.circuit_name = (magma_opts["user_namespace"] + "_" +
                                 self.circuit_name)

        if hasattr(circuit, "verilog_file_name") and \
                os.path.splitext(circuit.verilog_file_name)[-1] == ".sv" or \
                use_kratos or "sv" in self.magma_opts:
            suffix = "sv"
        else:
            suffix = "v"
        self.verilog_file = Path(f"{self.circuit_name}.{suffix}")
        # Optionally compile this module to verilog first.
        if not self.skip_compile:
            prefix = os.path.splitext(self.directory / self.verilog_file)[0]
            m.compile(prefix, self.circuit, output=self.magma_output,
                      **self.magma_opts)
            if use_kratos:
                # kratos generates SystemVerilog file
                # Until magma/coreir can generate sv suffix, we have to move
                # the files around
                os.rename(prefix + ".v", prefix + ".sv")
            if not (self.directory / self.verilog_file).is_file():
                raise Exception(f"Compiling {self.circuit} failed")

        self.assumptions = []
        self.guarantees = []

        # set up value file for storing user-accessible resuls
        value_file_path = (Path(self.directory) / value_file_name).resolve()
        self.value_file = File(name=str(value_file_path), tester=None,
                               mode='w', chunk_size=None, endianness=None)
        # coverage
        self.coverage = coverage

    @abstractmethod
    def compile_expression(self, value):
        pass

    def make_assume(self, i, action):
        self.assumptions.append(action)
        return ""

    def make_guarantee(self, i, action):
        self.guarantees.append(action)
        return ""

    def generate_array_action_code(self, i, action):
        result = []
        port = action.port
        if isinstance(port, SelectPath):
            port = port[-1]
        for j in range(port.N):
            if isinstance(action, actions.Print):
                value = action.format_str
            else:
                value = action.value[j]
            result += [
                self.generate_action_code(
                    i, type(action)(port[j], value)
                )]
        return flatten(result)

    def generate_action_code(self, i, action):
        if isinstance(action, str):
            # if "action" is a string, assume it's a line of code, and return
            # a list containing just the string, with no further processing
            return [action]
        elif isinstance(action, list):
            # if "action" is a list, generate code for each element and then
            # concatenate the results
            return flatten([self.generate_action_code(i, elem)
                            for elem in action])
        elif isinstance(action, (actions.PortAction)) and \
                isinstance(action.port, m.Array) and \
                not issubclass(action.port.T, m.Digital):
            return self.generate_array_action_code(i, action)
        elif isinstance(action, (actions.PortAction)) and \
                isinstance(action.port, SelectPath) and \
                isinstance(action.port[-1], m.Array) and \
                not issubclass(action.port[-1].T, m.Digital):
            return self.generate_array_action_code(i, action)
        elif isinstance(action, actions.Poke):
            return self.make_poke(i, action)
        elif isinstance(action, actions.Print):
            return self.make_print(i, action)
        elif isinstance(action, actions.Expect):
            return self.make_expect(i, action)
        elif isinstance(action, actions.Eval):
            return self.make_eval(i, action)
        elif isinstance(action, actions.Step):
            return self.make_step(i, action)
        elif isinstance(action, actions.Assume):
            return self.make_assume(i, action)
        elif isinstance(action, actions.Guarantee):
            return self.make_guarantee(i, action)
        elif isinstance(action, actions.Loop):
            return self.make_loop(i, action)
        elif isinstance(action, actions.FileOpen):
            return self.make_file_open(i, action)
        elif isinstance(action, actions.FileWrite):
            return self.make_file_write(i, action)
        elif isinstance(action, actions.FileRead):
            return self.make_file_read(i, action)
        elif isinstance(action, actions.FileClose):
            return self.make_file_close(i, action)
        elif isinstance(action, actions.While):
            return self.make_while(i, action)
        elif isinstance(action, actions.If):
            return self.make_if(i, action)
        elif isinstance(action, actions.Var):
            return self.make_var(i, action)
        elif isinstance(action, actions.FileScanFormat):
            return self.make_file_scan_format(i, action)
        elif isinstance(action, actions.Delay):
            return self.make_delay(i, action)
        elif isinstance(action, actions.GetValue):
            return self.make_get_value(i, action)
        elif isinstance(action, actions.Assert):
            return self.make_assert(i, action)
        raise NotImplementedError(action)

    @abstractmethod
    def make_poke(self, i, action):
        pass

    @abstractmethod
    def make_print(self, i, action):
        pass

    @abstractmethod
    def make_expect(self, i, action):
        pass

    @abstractmethod
    def make_eval(self, i, action):
        pass

    @abstractmethod
    def make_step(self, i, action):
        pass

    def make_loop(self, i, action):
        # determine type of the loop variable (typically int or None)
        loop_var_type = f'{self.LOOP_VAR_TYPE} ' if self.LOOP_VAR_TYPE else ''

        # construct the "for" loop condition
        if action.count == 'up':
            cond = '; '.join([
                f'{loop_var_type}{action.loop_var} = 0',
                f'{action.loop_var} < {action.n_iter}',
                f'{action.loop_var}++'
            ])
        elif action.count == 'down':
            cond = '; '.join([
                f'{loop_var_type}{action.loop_var} = {action.n_iter - 1}',
                f'{action.loop_var} >= 0',
                f'{action.loop_var}--'
            ])
        else:
            raise ValueError(f'Unknown count direction: {action.count}.')

        # return code representing the for loop
        return self.make_block(i, 'for', cond, action.actions)

    @abstractmethod
    def make_file_open(self, i, action):
        pass

    @abstractmethod
    def make_file_close(self, i, action):
        pass

    @abstractmethod
    def make_file_read(self, i, action):
        pass

    @abstractmethod
    def make_file_write(self, i, action):
        pass

    @abstractmethod
    def make_file_scan_format(self, i, action):
        pass

    @abstractmethod
    def make_var(self, i, action):
        pass

    @abstractmethod
    def make_delay(self, i, action):
        pass

    def make_while(self, i, action):
        cond = self.compile_expression(action.loop_cond)
        return self.make_block(i, 'while', cond, action.actions)

    def make_if(self, i, action):
        # get code for if statement
        cond = self.compile_expression(action.cond)
        if_code = self.make_block(i, 'if', cond, action.actions)

        # add code for else statement (if needed)
        if not action.else_actions:
            return if_code
        else:
            else_code = self.make_block(i, 'else', None, action.else_actions)
            else_code[0] = f'{self.BLOCK_END} else {self.BLOCK_START}'
            return if_code[:-1] + else_code

    @abstractmethod
    def make_get_value(self, i, action):
        pass

    @abstractmethod
    def make_assert(self, i, action):
        pass

    def make_block(self, i, name, cond, actions):
        '''
        Generic function that creates a properly indented code block.  This
        is useful for constructing "if", "while", and "for" blocks
        Format:
        {name} ({cond}) BLOCK_START
            actions[0]
            actions[1]
            ...
        BLOCK_END
        '''

        # set defaults
        if actions is None:
            actions = []

        # build up the code block
        code = []
        if cond is not None:
            code += [f'{name} ({cond}) {self.BLOCK_START}']
        else:
            code += [f'{name} {self.BLOCK_START}']
        code += [f'{self.TAB}{line}'
                 for line in self.generate_action_code(i, actions)]
        code += [f'{self.BLOCK_END}']

        # return the code block
        return code

    def post_process_get_value_actions(self, all_actions):
        get_value_actions = [action for action in all_actions
                             if isinstance(action, actions.GetValue)]
        if len(get_value_actions) > 0:
            with open(self.value_file.name, 'r') as f:
                lines = f.readlines()
            for line, action in zip(lines, get_value_actions):
                action.update_from_line(line)

    @staticmethod
    def in_var(file):
        '''Name of variable used to read in contents of file.'''
        return f'{file.name_without_ext}_in'

    @staticmethod
    def fd_var(file):
        '''Name of variable used to hold the file descriptor.'''
        return f'{file.name_without_ext}_file'
