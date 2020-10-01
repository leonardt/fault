import pytest

import magma as m
import fault


@pytest.mark.parametrize('TesterClass', [fault.Tester,
                                         fault.SynchronousTester])
def test_inherit_methods(TesterClass):
    class DUT(m.Circuit):
        io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit)) + m.ClockIO()

    tester = TesterClass(DUT, DUT.CLK)
    assert isinstance(tester._if(tester.circuit.O), TesterClass)
    assert isinstance(tester._while(tester.circuit.O), TesterClass)
