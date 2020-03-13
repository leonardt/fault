import magma as m
import fault
from fault.spice_target import SpiceTarget


def test_spice_port_order():
    # declare a circuit with
    class circ(m.Circuit):
        name = 's'
        io = m.IO(
            p=fault.ElectIn,
            i=m.BitIn,
            c=m.Out(m.Bits[3]),
            e=fault.RealOut
        )

    target = SpiceTarget(circ, conn_order='alpha')

    ports = target.get_ordered_ports()

    assert ports == ['c<2>', 'c<1>', 'c<0>', 'e', 'i', 'p']
