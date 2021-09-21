import magma as m
from fault.tester.staged_tester import Tester
from fault.assert_immediate import assert_immediate


class ReadyValidTester:
    def __init__(self, circuit: m.Circuit, sequences: dict):
        class Wrapper(m.Circuit):
            io = m.IO(done=m.Out(m.Bit))
            inst = circuit()
            done = m.Bit(1)
            for key, value in sequences.items():
                port = getattr(inst, key)
                n = len(value)
                count = m.Register(m.UInt[(n - 1).bit_length()],
                                   has_enable=True)()
                # NOTE: Here we can add logic for random stalls
                count.I @= count.O + 1
                port_T = type(port)
                curr = m.mux(value, count.O)
                if port_T.is_consumer():
                    count.CE @= (count.O != (n - 1)) & port.ready
                    port.data @= curr
                    port.valid @= (count.O != (n - 1))
                else:
                    count.CE @= (count.O != (n - 1)) & port.valid
                    port.ready @= (count.O != (n - 1))
                    assert_immediate(~((count.O != (n - 1)) & port.valid) |
                                     (port.data == curr))
                done = done & (count.O == (n - 1))
            io.done @= done

        self.circuit = Wrapper

    def compile_and_run(self, *args, **kwargs):
        tester = Tester(self.circuit)
        tester.wait_until_high(self.circuit.done)
        tester.compile_and_run(*args, **kwargs)
