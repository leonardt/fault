from pathlib import Path
import subprocess
import magma
import fault.actions as actions
from fault.target import Target
import fault.value_utils as value_utils
import fault.verilator_utils as verilator_utils


src_tpl = """\
{includes}

void my_assert(
    unsigned int got,
    unsigned int expected,
    int i,
    const char* port) {{
  if (got != expected) {{
    std::cerr << std::endl;  // end the current line
    std::cerr << \"Got      : \" << got << std::endl;
    std::cerr << \"Expected : \" << expected << std::endl;
    std::cerr << \"i        : \" << i << std::endl;
    std::cerr << \"Port     : \" << port << std::endl;
    exit(1);
  }}
}}

int main(int argc, char **argv) {{
  Verilated::commandArgs(argc, argv);
  V{circuit_name}* top = new V{circuit_name};

{main_body}

}}
"""


class VerilatorTarget(Target):
    def __init__(self, circuit, actions, directory="build/",
                 flags=[], skip_compile=False, include_verilog_files=[]):
        super().__init__(circuit, actions)
        self.directory = Path(directory)
        self.flags = flags
        self.skip_compile = skip_compile
        self.include_verilog_files = include_verilog_files

    @staticmethod
    def generate_action_code(i, action):
        if isinstance(action, actions.Poke):
            name = verilator_utils.verilator_name(action.port.name)
            return [f"top->{name} = {action.value};"]
        if isinstance(action, actions.Expect):
            # For verilator, if an expect is "AnyValue" we don't need to perform
            # the expect.
            if value_utils.is_any(action.value):
                return []
            name = verilator_utils.verilator_name(action.port.name)
            return [f"my_assert(top->{name}, {action.value}, "
                    f"{i}, \"{action.port.name}\");"]
        if isinstance(action, actions.Eval):
            return ["top->eval();"]
        if isinstance(action, actions.Step):
            name = verilator_utils.verilator_name(action.clock.name)
            code = []
            for step in range(action.steps):
                code.append("top->eval();")
                code.append(f"top->{name} ^= 1;")
            return code
        raise NotImplementedError(action)

    def generate_code(self):
        circuit_name = self.circuit.name
        includes = [
            f'"V{circuit_name}.h"',
            '"verilated.h"',
            '<iostream>',
        ]

        main_body = ""
        for i, action in enumerate(self.actions):
            code = VerilatorTarget.generate_action_code(i, action)
            for line in code:
                main_body += f"  {line}\n"

        includes_src = "\n".join(["#include " + i for i in includes])
        src = src_tpl.format(
            includes=includes_src,
            main_body=main_body,
            circuit_name=circuit_name,
        )

        return src

    def run_from_directory(self, cmd):
        return subprocess.call(cmd, cwd=self.directory, shell=True)

    def run(self):
        verilog_file = self.directory / Path(f"{self.circuit.name}.v")
        driver_file = self.directory / Path(f"{self.circuit.name}_driver.cpp")
        top = self.circuit.name
        # Optionally compile this module to verilog first.
        if not self.skip_compile:
            prefix = str(verilog_file)[:-2]
            magma.compile(prefix, self.circuit, output="verilog")
        assert verilog_file.is_file()
        # Write the verilator driver to file.
        src = self.generate_code()
        with open(driver_file, "w") as f:
            f.write(src)
        # Run a series of commands: compile the design using 'verilator', run
        # the Makefile output by verilator, and finally run the executable
        # created by verilator.
        verilator_cmd = verilator_utils.verilator_cmd(
            top, verilog_file.name, self.include_verilog_files,
            driver_file.name, self.flags)
        assert not self.run_from_directory(verilator_cmd)
        verilator_make_cmd = verilator_utils.verilator_make_cmd(top)
        assert not self.run_from_directory(verilator_make_cmd)
        assert not self.run_from_directory(f"./obj_dir/V{top}")
