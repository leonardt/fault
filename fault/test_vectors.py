from magma import BitKind, ArrayKind, SIntKind, UIntKind, BitsKind
from magma.simulator.python_simulator import PythonSimulator
from hwtypes import BitVector, SIntVector, UIntVector
from inspect import signature
from itertools import product
import pytest
import fault


class TestVector:
    __test__ = False

    def __init__(self, test_vector):
        self.test_vector = test_vector

    def __eq__(self, other):
        if not isinstance(other, TestVector):
            raise ValueError("Expected another TestVector for __eq__")
        for x, y in zip(self, other):
            if x is fault.AnyValue or y is fault.AnyValue:
                continue
            if x != y:
                return False
        return True

    def __len__(self):
        return len(self.test_vector)

    def __iter__(self):
        return iter(self.test_vector)

    def __str__(self):
        return str(self.test_vector)

    def __repr__(self):
        return repr(self.test_vector)


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


def flatten_tests(tests):
    flattened_tests = []
    for i in range(len(tests)):
        flattened_tests.append(tests[i][0][:])
        if i == 0:
            flattened_tests[-1].extend(
                [fault.AnyValue for _ in range(len(tests[i][1]))])
        else:
            flattened_tests[-1].extend(tests[i - 1][1])
    flattened_tests.append(tests[-1][0][:])
    flattened_tests[-1].extend(tests[-1][1])
    return [TestVector(x) for x in flattened_tests]


@pytest.mark.skip(reason="Not a test")
def generate_function_test_vectors(circuit, func, input_ranges=None,
                                   mode='complete', flatten=True):
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
                        input_range = range(-2**(num_bits - 1),
                                            2**(num_bits - 1))
                    else:
                        input_range = input_ranges[i]
                    args.append([SIntVector[num_bits](x)
                                 for x in input_range])
                else:
                    if input_ranges is None:
                        input_range = range(1 << num_bits)
                    else:
                        input_range = input_ranges[i]
                    args.append([BitVector[num_bits](x)
                                 for x in input_range])
            else:
                raise NotImplementedError(type(port))

    tests = []
    for test in product(*args):
        result = func(*list(test))
        test = [list(test), []]
        if isinstance(result, tuple):
            test[-1].extend(result)
        else:
            test[-1].append(result)
        tests.append(test)
    if flatten:
        tests = flatten_tests(tests)
    else:
        tests = [test[0] + test[1] for test in tests]
    return tests


def generate_simulator_test_vectors(circuit, input_ranges=None,
                                    mode='complete', flatten=True):
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
                    args.append([SIntVector[num_bits](x)
                                 for x in input_range])
                else:
                    if input_ranges is None:
                        input_range = range(1 << num_bits)
                    else:
                        input_range = input_ranges[i]
                    args.append([BitVector[num_bits](x)
                                 for x in input_range])
            else:
                assert True, "can't test Tuples"

    tests = []
    for test in product(*args):
        testv = [list(test), []]
        j = 0
        for i, (name, port) in enumerate(circuit.IO.items()):
            if port.isinput():
                val = test[j].as_bool_list()
                if len(val) == 1:
                    val = val[0]
                simulator.set_value(getattr(circuit, name), val)
                j += 1

        simulator.evaluate()

        for i, (name, port) in enumerate(circuit.IO.items()):
            if port.isoutput():
                val = simulator.get_value(getattr(circuit, name))
                if isinstance(port, ArrayKind) and \
                        not isinstance(port, (BitsKind, SIntKind, UIntKind)):
                    val = BitVector(val)
                testv[1].append(val)

        tests.append(testv)

    if flatten:
        tests = flatten_tests(tests)
    else:
        tests = [test[0] + test[1] for test in tests]
    return tests
