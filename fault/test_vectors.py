from inspect import signature
from itertools import product
import pytest
from bit_vector import BitVector, UIntVector, SIntVector
from magma import BitType, ArrayType, BitsType, UIntType, SIntType
from magma.simulator.python_simulator import PythonSimulator
from magma.bitutils import seq2int


# check that number of function arguments equals number of circuit inputs
def check(circuit, func):
    sig = signature(func)
    nfuncargs = len(sig.parameters)

    # count circuit inputs
    ncircargs = 0
    for name, port in circuit.interface.ports.items():
        if port.isoutput():
            ncircargs += 1

    assert nfuncargs == ncircargs

def generate_args(circuit, input_ranges, strategy='complete'):
    args = []
    for i, (name, port) in enumerate(circuit.interface.ports.items()):
        if port.isoutput():
            if isinstance(port, BitType):
                args.append([BitVector(0), BitVector(1)])
            elif isinstance(port, ArrayType):
                num_bits = type(port).N
                if isinstance(port, SIntType):
                    if input_ranges is None:
                        start = -2**(num_bits - 1)
                        # We don't subtract one because range end is exclusive
                        end = 2**(num_bits - 1)
                        input_range = range(start, end)
                    else:
                        input_range = input_ranges[i]
                    args.append([SintVector(x, num_bits=num_bits)
                                 for x in input_range])
                elif isinstance(port, (UIntType, BitsType)):
                    if input_ranges is None:
                        input_range = range(1 << num_bits)
                    else:
                        input_range = input_ranges[i]
                    if isinstance(port, UIntType):
                        args.append([UIntVector(x, num_bits=num_bits)
                                 for x in input_range])
                    else:
                        args.append([BitVector(x, num_bits=num_bits)
                                 for x in input_range])
            else:
                assert True, "can't test Tuples"
    return args


@pytest.mark.skip(reason="Not a test")
def generate_function_test_vectors(circuit, func, input_ranges=None,
                                   strategy='complete'):
    check(circuit, func)

    args = generate_args(circuit, input_ranges, strategy=strategy)

    tests = []
    for test in product(*args):
        test = list(test)
        result = func(*test)
        if isinstance(result, tuple):
            test.extend(result)
        else:
            test.append(result)
        tests.append(test)

    return tests


def generate_simulator_test_vectors(circuit, input_ranges=None,
                                    strategy='complete'):
    ntest = len(circuit.interface.ports.items())

    args = generate_args(circuit, input_ranges, strategy=strategy)

    simulator = PythonSimulator(circuit)

    tests = []
    for test in product(*args):
        test = list(test)
        testv = ntest*[0]
        j = 0
        for i, (name, port) in enumerate(circuit.interface.ports.items()):
            # circuit defn output is an input to the idefinition
            if port.isoutput():
                testv[i] = test[j].as_int()
                val = test[j].as_bool_list()
                if len(val) == 1:
                    val = val[0]
                simulator.set_value(getattr(circuit, name), val)
                j += 1

        simulator.evaluate()

        for i, (name, port) in enumerate(circuit.interface.ports.items()):
            # circuit defn input is an input of the definition
            if port.isinput():
                val = simulator.get_value(getattr(circuit, name))
                # check for other types
                if isinstance(port, (BitsType, BitType)):
                    val = BitVector(val)
                elif isinstance(port, UIntType):
                    val = UIntVector(val)
                elif isinstance(port, SIntType):
                    val = SIntVector(val)
                testv[i] = int(val)

        tests.append(testv)

    return tests
