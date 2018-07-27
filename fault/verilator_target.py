from .target import Target
from fault.test_vectors import generate_function_test_vectors
import magma.config as config
import inspect
import os
import subprocess
import magma as m
from .array import Array


def flattened_names(arr):
    if isinstance(arr.T, m.ArrayKind):
        names = [f"_{i}" for i in range(len(arr))]
        prod_names = []
        for name_0 in flattened_names(arr.T):
            for name_1 in names:
                prod_names.append(f"{name_1}{name_0}")
        return prod_names

    elif not isinstance(arr.T, m._BitKind):
        raise NotImplementedError()
    return [""]


def harness(circuit, tests):

    assert len(circuit.interface.ports.keys()) == len(tests[0])

    test_vector_length = 0
    for item in tests[0]:
        if isinstance(item, Array):
            test_vector_length += item.flattened_length
        else:
            test_vector_length += 1

    source = '''\
#include "V{name}.h"
#include "verilated.h"
#include <cassert>
#include <iostream>

typedef struct {{
    unsigned int value;
    bool is_x;
}} value_t;

void check(const char* port, int a, value_t b, int i) {{
    if (!b.is_x) {{
        std::cerr << port << "=" << b.value << ", ";
    }}
    if (!b.is_x && !(a == b.value)) {{
        std::cerr << std::endl;  // end the current line
        std::cerr << \"Got      : \" << a << std::endl;
        std::cerr << \"Expected : \" << b.value << std::endl;
        std::cerr << \"i        : \" << i << std::endl;
        std::cerr << \"Port     : \" << port << std::endl;

        exit(1);
    }}
}}

int main(int argc, char **argv, char **env) {{
    Verilated::commandArgs(argc, argv);
    V{name}* top = new V{name};
'''.format(name=circuit.__name__)

    source += '''
    value_t tests[{}][{}] = {{
'''.format(len(tests), test_vector_length)

    for i, test in enumerate(tests):
        testvector = []

        def to_string(t):
            if t is None or t._value is None:
                val = "0"
                X = "true"
            else:
                val = t.as_binary_string()
                X = "false"
            return f"{{{val}, {X}}}"

        for t in test:
            if isinstance(t, Array):
                testvector.extend(t.flattened())
            else:
                testvector.append(t)
        names = []
        for name, port in circuit.interface.ports.items():
            if isinstance(port, m.ArrayType):
                names.extend(f"{name}{x}" for x in flattened_names(port))
            else:
                names.append(name)
        testvector = '\n            '.join(
            [f"{to_string(t)},  // {name}"
             for t, name in zip(testvector, names)])
        # testvector += ', {}'.format(int(func(*test[:nargs])))
        source += f'''\
        {{  // {i}
            {testvector}
        }},
'''
    source += '''\
    };
'''

    source += '''
    for(int i = 0; i < {}; i++) {{
        value_t* test = tests[i];

        std::cerr << "Inputs: ";
'''.format(len(tests))

    i = 0
    output_str = ""
    for name, port in circuit.interface.ports.items():
        if port.isoutput():
            if isinstance(port, m.ArrayType) and \
                    not isinstance(port.T, m._BitType):
                for _name in flattened_names(port):
                    source += f'''\
        top->{name}{_name} = test[{i}].value;
        std::cerr << "top->{name}{_name} = " << test[{i}].value << ", ";
'''
                    i += 1

            else:
                source += f'''\
        top->{name} = test[{i}].value;
        std::cerr << "top->{name} = " << test[{i}].value << ", ";
'''
                i += 1
        else:
            if isinstance(port, m.ArrayType) and \
                    not isinstance(port.T, m._BitType):
                for _name in flattened_names(port):
                    output_str += f'''\
        check(\"{name}{_name}\", top->{name}{_name}, test[{i}], i);
'''
                    i += 1
            else:
                output_str += f'''\
        check(\"{name}\", top->{name}, test[{i}], i);
'''
                i += 1

    source += f'''\
        std::cerr << std::endl;
        std::cerr << "Checking Outputs: ";
{output_str}
        std::cerr << std::endl;
        top->eval();
        std::cerr << "{"="*80}" << std::endl;
'''
    source += '''\
    }
'''

    source += '''
    delete top;
    std::cout << "Success" << std::endl;
    exit(0);
}'''

    return source


def compile_verilator_harness(basename, circuit, tests, input_ranges=None):
    if config.get_compile_dir() == 'callee_file_dir':
        (_, filename, _, _, _, _) = \
            inspect.getouterframes(inspect.currentframe())[1]
        file_path = os.path.dirname(filename)
        filename = os.path.join(file_path, basename)
    else:
        filename = basename

    if callable(tests):
        tests = generate_function_test_vectors(circuit, tests, input_ranges)
    verilatorcpp = harness(circuit, tests)

    with open(filename, "w") as f:
        f.write(verilatorcpp)


def run_verilator_test(verilog_file_name, driver_name, top_module,
                       verilator_flags="", build_dir="build"):
    if isinstance(verilator_flags, list):
        if not all(isinstance(flag, str) for flag in verilator_flags):
            raise ValueError("verilator_flags should be a str or list of strs")
        verilator_flags = " ".join(verilator_flags)
    assert not subprocess.call(
        f'verilator -Wall -Wno-INCABSPATH -Wno-DECLFILENAME {verilator_flags}'
        f' --cc {verilog_file_name}.v --exe {driver_name}.cpp'
        f' --top-module {top_module}',
        cwd=build_dir, shell=True
    )
    assert not subprocess.call(
        f'make -C obj_dir -j -f V{top_module}.mk V{top_module}', cwd=build_dir,
        shell=True)
    assert not subprocess.call('./obj_dir/V{}'.format(top_module),
                               cwd=build_dir, shell=True)


class VerilatorTarget(Target):
    def __init__(self, circuit, test_vectors, directory="build/", flags=[]):
        super().__init__(circuit, test_vectors)
        self._directory = directory
        self._flags = flags

    def run(self):
        compile_verilator_harness(
            f"{self._directory}/test_{self._circuit.name}.cpp", self._circuit,
            self._test_vectors)
        run_verilator_test(
            self._circuit.name, f"test_{self._circuit.name}",
            self._circuit.name, self._flags, build_dir=self._directory)
