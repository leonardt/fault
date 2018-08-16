from magma import BitKind, ArrayKind, SIntKind, TupleKind
from magma.simulator.python_simulator import PythonSimulator
from bit_vector import BitVector, SIntVector
from inspect import signature
from itertools import product
import pytest


# check that number of function arguments equals number of circuit inputs
def check(circuit, func):
    sig = signature(func)
    nfuncargs = len(sig.parameters)

    # count circuit inputs
    ncircargs = 0
    for name, port in circuit.IO.items():
        if port.isinput():
            ncircargs += 1

    assert nfuncargs == ncircargs


@pytest.mark.skip(reason="Not a test")
def generate_function_test_vectors(circuit, func, input_ranges=None,
                                   mode='complete'):
    check(circuit, func)

    args = []
    for i, (name, port) in enumerate(circuit.IO.items()):
        if port.isinput():
            if isinstance(port, BitKind):
                args.append([BitVector(0), BitVector(1)])
            elif isinstance(port, ArrayKind) and isinstance(port.T, BitKind):
                num_bits = port.N
                if isinstance(port, SIntKind):
                    if input_ranges is None:
                        input_range = range(-2**(num_bits-1), 2**(num_bits-1))
                    else:
                        input_range = input_ranges[i]
                    args.append([SIntVector(x, num_bits=num_bits)
                                 for x in input_range])
                else:
                    if input_ranges is None:
                        input_range = range(1 << num_bits)
                    else:
                        input_range = input_ranges[i]
                    args.append([BitVector(x, num_bits=num_bits)
                                 for x in input_range])
            else:
                raise NotImplementedError(type(port))

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
                                    mode='complete'):
    ntest = len(circuit.interface.ports.items())

    simulator = PythonSimulator(circuit)

    args = []
    for i, (name, port) in enumerate(circuit.IO.items()):
        if port.isinput():
            if isinstance(port, BitKind):
                args.append([BitVector(0), BitVector(1)])
            elif isinstance(port, ArrayKind) and isinstance(port.T, BitKind):
                num_bits = port.N
                if isinstance(port, SIntKind):
                    if input_ranges is None:
                        start = -2**(num_bits - 1)
                        # We don't subtract one because range end is exclusive
                        end = 2**(num_bits - 1)
                        input_range = range(start, end)
                    else:
                        input_range = input_ranges[i]
                    args.append([SIntVector(x, num_bits=num_bits)
                                 for x in input_range])
                else:
                    if input_ranges is None:
                        input_range = range(1 << num_bits)
                    else:
                        input_range = input_ranges[i]
                    args.append([BitVector(x, num_bits=num_bits)
                                 for x in input_range])
            else:
                assert True, "can't test Tuples"

    tests = []
    for test in product(*args):
        test = list(test)
        testv = ntest*[0]
        j = 0
        for i, (name, port) in enumerate(circuit.IO.items()):
            if port.isinput():
                if isinstance(port, SIntKind):
                    testv[i] = test[j].as_sint()
                else:
                    testv[i] = test[j].as_uint()
                val = test[j].as_bool_list()
                if len(val) == 1:
                    val = val[0]
                simulator.set_value(getattr(circuit, name), val)
                j += 1

        simulator.evaluate()

        for i, (name, port) in enumerate(circuit.IO.items()):
            if port.isoutput():
                val = simulator.get_value(getattr(circuit, name))
                if isinstance(port, SIntKind):
                    val = SIntVector(val).as_sint()
                else:
                    val = BitVector(val).as_uint()
                testv[i] = val

        tests.append(testv)

    return tests
