from .array import Array
from pathlib import Path
import subprocess
import magma as m
import fault.actions as actions
from fault.verilog_target import VerilogTarget, verilog_name
import fault.value_utils as value_utils
import fault.verilator_utils as verilator_utils
import math
from bit_vector import BitVector, SIntVector


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
                 circuit_name=None):
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
                         magma_output)
        self.flags = flags
        self.include_verilog_libraries = include_verilog_libraries
        self.include_directories = include_directories

        # Compile the design using `verilator`
        driver_file = self.directory / Path(f"{self.circuit_name}_driver.cpp")
        verilator_cmd = verilator_utils.verilator_cmd(
            self.circuit_name, self.verilog_file.name,
            self.include_verilog_libraries, self.include_directories,
            driver_file.name, self.flags)
        if self.run_from_directory(verilator_cmd):
            raise Exception(f"Running verilator cmd {verilator_cmd} failed")

    def make_poke(self, i, action):
        name = verilog_name(action.port.name)
        if isinstance(action.value, BitVector) and \
                action.value.num_bits > 32:
            asserts = []
            for i in range(math.ceil(action.value.num_bits / 32)):
                value = action.value[i * 32:min(
                    (i+1) * 32, action.value.num_bits)]
                asserts += [f"top->{name}[{i}] = {value};"]
            return asserts
        else:
            value = action.value
            if isinstance(action.port, m.SIntType) and value < 0:
                # Handle sign extension for verilator since it expects and
                # unsigned c type
                port_len = len(action.port)
                value = BitVector(value, port_len).as_uint()
            return [f"top->{name} = {value};"]

    def make_print(self, i, action):
        name = verilog_name(action.port.name)
        return [f'printf("{action.port.debug_name} = '
                f'{action.format_str}\\n", top->{name});']

    def make_expect(self, i, action):
        # For verilator, if an expect is "AnyValue" we don't need to
        # perform the expect.
        if value_utils.is_any(action.value):
            return []
        name = verilog_name(action.port.name)
        value = action.value
        if isinstance(value, actions.Peek):
            value = f"top->{value.port.name}"
        elif isinstance(action.port, m.SIntType) and value < 0:
            # Handle sign extension for verilator since it expects and
            # unsigned c type
            port_len = len(action.port)
            value = BitVector(value, port_len).as_uint()

        return [f"my_assert(top->{name}, {value}, "
                f"{i}, \"{action.port.name}\");"]

    def make_eval(self, i, action):
        return ["top->eval();", "main_time++;", "#if VM_TRACE",
                "tracer->dump(main_time);", "#endif"]

    def make_step(self, i, action):
        name = verilog_name(action.clock.name)
        code = []
        for step in range(action.steps):
            code.append("top->eval();")
            code.append("main_time++;")
            code.append("#if VM_TRACE")
            code.append("tracer->dump(main_time);")
            code.append("#endif")
            code.append(f"top->{name} ^= 1;")
        return code

    def generate_code(self, actions):
        includes = [
            f'"V{self.circuit_name}.h"',
            '"verilated.h"',
            '<iostream>',
            '<verilated_vcd_c.h>',
            '<sys/types.h>',
            '<sys/stat.h>',
        ]

        main_body = ""
        for i, action in enumerate(actions):
            code = self.generate_action_code(i, action)
            for line in code:
                main_body += f"  {line}\n"

        includes_src = "\n".join(["#include " + i for i in includes])
        src = src_tpl.format(
            includes=includes_src,
            main_body=main_body,
            circuit_name=self.circuit_name,
        )

        return src

    def run_from_directory(self, cmd):
        return subprocess.call(cmd, cwd=self.directory, shell=True)

    def run(self, actions):
        driver_file = self.directory / Path(f"{self.circuit_name}_driver.cpp")
        # Write the verilator driver to file.
        src = self.generate_code(actions)
        with open(driver_file, "w") as f:
            f.write(src)
        # Run a series of commands: run the Makefile output by verilator, and
        # finally run the executable created by verilator.
        verilator_make_cmd = verilator_utils.verilator_make_cmd(
            self.circuit_name)
        assert not self.run_from_directory(verilator_make_cmd)
        assert not self.run_from_directory(f"./obj_dir/V{self.circuit_name}")
