import tempfile
import magma as m
import fault.python_simulator_target
from bit_vector import BitVector
import mantle


def test_python_simulator_target():
    """
    Test basic python simulator workflow with a simple circuit.
    """

    class Foo(m.Circuit):
        IO = ["I", m.In(m.Bit), "O", m.Out(m.Bit)]

        @classmethod
        def definition(io):
            m.wire(io.I, io.O)

    def bit(val):
        return BitVector(val, 1)

    test_vectors = [
        [bit(0), bit(0),],
        [bit(1), bit(1),],
    ]
    target = fault.python_simulator_target.PythonSimulatorTarget(
        Foo, test_vectors, None)
    target.run()
